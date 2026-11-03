"""Single-queue models adhering to Kendall notation for bkitevsim.

Hiện thực các trạm trong mô hình hàng đợi đơn Kendall:
SourceLP (Sinh tải Poisson), QueueServerLP (Server & Bộ đệm), SinkLP (Thu gom).
"""

from __future__ import annotations
import random
from collections import deque
from typing import Any, Deque, Dict, List, Optional
from bkitevsim.core.event import Event, create_event
from bkitevsim.core.logical_process import BkSysLogicalProcess
from bkitevsim.utils.metrics import MetricsCollector


class Job:
    """Đại diện cho một gói tin / khách hàng / tác vụ trong hệ thống hàng đợi."""

    def __init__(self, job_id: int, arrival_time: float) -> None:
        self.job_id = job_id
        self.orig_arrival_time = arrival_time
        self.arrival_time = arrival_time
        self.start_service_time: Optional[float] = None
        self.departure_time: Optional[float] = None


class SourceLP(BkSysLogicalProcess):
    """Tiến trình Logic phát sinh lưu lượng theo quá trình Poisson (Inter-arrival ~ Exp(lambda))."""

    def __init__(
        self,
        lp_id: int | str = "Source",
        dest_lp_id: int | str = "Server",
        arrival_rate: float = 1.0,
        burst_prob: float = 0.0,
        burst_size: int = 5
    ) -> None:
        super().__init__(lp_id)
        self.dest_lp_id = dest_lp_id
        self.arrival_rate = arrival_rate
        self.burst_prob = burst_prob
        self.burst_size = burst_size
        self._job_counter: int = 0
        self._started: bool = False

    def initialize(self) -> None:
        """Kích hoạt gói tin đầu tiên khi Dispatcher khởi tạo."""
        self.start()

    def start(self) -> None:
        """Lập lịch sự kiện ARRIVAL đầu tiên (đảm bảo tính idempotent tránh lặp sự kiện)."""
        if self._started:
            return
        self._started = True
        if self.arrival_rate > 0:
            # Lấy mẫu thời gian đến kế tiếp theo phân phối hàm mũ Exp(lambda)
            delay = random.expovariate(self.arrival_rate)
            ev = create_event(
                timestamp=self.local_virt_time + delay,
                sender_id=self.lp_id,
                receiver_id=self.lp_id,
                event_type="ARRIVAL"
            )
            self.send_event(ev)

    def reset(self) -> None:
        """Đặt lại bộ đếm job và cờ trạng thái cho lượt chạy mới."""
        super().reset()
        self._job_counter = 0
        self._started = False

    def handle_event(self, event: Event) -> None:
        """Tạo job gửi sang Server, sau đó tự lập lịch sự kiện đến tiếp theo."""
        super().handle_event(event)
        etype = str(event.event_type).upper()
        if etype in ("ARRIVAL", "EVENTTYPE.ARRIVAL"):
            # 1. Xác định số lượng gói tin trong đợt đến (đột biến burst hoặc đơn lẻ 1)
            batch = self.burst_size if (random.random() < self.burst_prob) else 1
            for _ in range(batch):
                self._job_counter += 1
                job = Job(self._job_counter, event.timestamp)
                # Bắn sự kiện ARRIVAL kèm job sang trạm Server
                job_ev = create_event(
                    timestamp=event.timestamp,
                    sender_id=self.lp_id,
                    receiver_id=self.dest_lp_id,
                    event_type="ARRIVAL",
                    payload={"job": job}
                )
                self.send_event(job_ev)

            # 2. Lập lịch sự kiện ARRIVAL tiếp theo theo phân phối Poisson Exp(lambda)
            next_delay = random.expovariate(self.arrival_rate)
            next_ev = create_event(
                timestamp=event.timestamp + next_delay,
                sender_id=self.lp_id,
                receiver_id=self.lp_id,
                event_type="ARRIVAL"
            )
            self.send_event(next_ev)


class QueueServerLP(BkSysLogicalProcess):
    """Trạm phục vụ thống nhất cho toàn bộ 6 mô hình Kendall (M/M/1, M/M/1/K, M/M/c, M/M/c/K,...)."""

    def __init__(
        self,
        lp_id: int | str = "Server",
        dest_lp_id: int | str = "Sink",
        service_rate: float = 1.0,
        num_servers: float = 1,
        capacity: Optional[int] = None,
        metrics: Optional[MetricsCollector] = None
    ) -> None:
        super().__init__(lp_id)
        self.dest_lp_id = dest_lp_id
        self.service_rate = service_rate
        self.num_servers = num_servers
        self.capacity = capacity
        self.metrics = metrics or MetricsCollector()
        self.waiting_queue: Deque[Job] = deque()     # Hàng chờ FIFO
        self.busy_servers: int = 0                  # Số máy chủ đang bận

    @property
    def total_in_system(self) -> int:
        """Tổng số khách đang có mặt trong trạm (đang phục vụ + đang xếp hàng)."""
        return self.busy_servers + len(self.waiting_queue)

    def handle_event(self, event: Event) -> None:
        """Phân luồng xử lý sự kiện ARRIVAL (khách đến) hoặc DEPARTURE (khách xong)."""
        super().handle_event(event)
        etype = str(event.event_type).upper()
        if etype in ("ARRIVAL", "EVENTTYPE.ARRIVAL"):
            self._handle_arrival(event)
        elif etype in ("DEPARTURE", "EVENTTYPE.DEPARTURE"):
            self._handle_departure(event)

    def _handle_arrival(self, event: Event) -> None:
        """Xử lý khách đến: nếu đầy đệm thì drop; nếu còn server rảnh thì phục vụ ngay; ngược lại xếp hàng."""
        job: Job = event.payload["job"] if isinstance(event.payload, dict) and "job" in event.payload else event.payload
        job.arrival_time = event.timestamp
        # Bước 1: Ghi nhận số lượng yêu cầu đến
        self.metrics.record_arrival()

        # Bước 2: Kiểm tra tràn bộ đệm (rớt gói nếu vượt sức chứa capacity)
        if self.capacity is not None and self.total_in_system >= self.capacity:
            self.metrics.record_drop()
            self._notify_state(event.timestamp)
            return

        # Bước 3: Phục vụ ngay nếu có server rảnh, hoặc đưa vào hàng chờ
        if self.busy_servers < self.num_servers:
            self.busy_servers += 1
            self._start_service(job, event.timestamp)
        else:
            self.waiting_queue.append(job)

        # Bước 4: Cập nhật tích phân thời gian trạng thái
        self._notify_state(event.timestamp)

    def _start_service(self, job: Job, current_time: float) -> None:
        """Lấy mẫu thời gian phục vụ ~ Exp(mu) và lập lịch sự kiện DEPARTURE."""
        job.start_service_time = current_time
        # Lấy mẫu thời gian phục vụ từ phân phối hàm mũ Exp(mu)
        service_duration = random.expovariate(self.service_rate)
        dep_ev = create_event(
            timestamp=current_time + service_duration,
            sender_id=self.lp_id,
            receiver_id=self.lp_id,
            event_type="DEPARTURE",
            payload={"job": job, "duration": service_duration}
        )
        self.send_event(dep_ev)

    def _handle_departure(self, event: Event) -> None:
        """Ghi nhận hoàn tất, gửi job tới trạm tiếp theo, và bốc khách tiếp theo trong hàng đợi (nếu có)."""
        payload = event.payload if isinstance(event.payload, dict) else {}
        job: Job = payload.get("job")
        service_duration = payload.get("duration", 0.0)

        # Bước 1: Tính toán thời gian chờ đợi và gửi job tới trạm đích Sink
        if job and job.start_service_time is not None:
            wait_time = job.start_service_time - job.arrival_time
            self.metrics.record_completion(wait_time, service_duration)
            job.departure_time = event.timestamp

            out_ev = create_event(
                timestamp=event.timestamp,
                sender_id=self.lp_id,
                receiver_id=self.dest_lp_id,
                event_type="ARRIVAL",
                payload={"job": job, "wait_time": wait_time, "service_time": service_duration}
            )
            self.send_event(out_ev)

        # Bước 2: Bốc khách tiếp theo trong hàng chờ vào phục vụ, hoặc giảm server bận
        if self.waiting_queue:
            next_job = self.waiting_queue.popleft()
            self._start_service(next_job, event.timestamp)
        else:
            self.busy_servers = max(0, self.busy_servers - 1)

        # Bước 3: Cập nhật tích phân thời gian trạng thái
        self._notify_state(event.timestamp)

    def _notify_state(self, current_time: float) -> None:
        """Cập nhật tích phân thời gian trạng thái hàng đợi cho bộ thu thập chỉ số."""
        self.metrics.update_state(
            current_time,
            q_len=len(self.waiting_queue),
            in_sys=self.total_in_system,
            busy_servers=self.busy_servers
        )

    def finalize(self) -> None:
        """Chốt số liệu đo lường khi kết thúc mô phỏng."""
        sim_time = self._dispatcher.current_time if self._dispatcher else self.local_virt_time
        self.metrics.finalize(sim_time)

    def get_metrics(self) -> Dict[str, Any]:
        """Lấy toàn bộ từ điển chỉ số hiệu năng (W, Wq, L, Lq, rho, throughput, drop_rate)."""
        sim_time = self._dispatcher.current_time if self._dispatcher else self.local_virt_time
        return self.metrics.finalize(sim_time)

    def reset(self) -> None:
        """Làm rỗng hàng đợi và đặt lại bộ đo lường."""
        super().reset()
        self.waiting_queue.clear()
        self.busy_servers = 0
        self.metrics.reset()


class SinkLP(BkSysLogicalProcess):
    """Trạm đích (Sink): Thu nhận các job đã xử lý xong và giải phóng Future bất đồng bộ."""

    def __init__(self, lp_id: int | str = "Sink", future_manager: Optional[Any] = None) -> None:
        super().__init__(lp_id)
        self.future_manager = future_manager
        self.completed_jobs: List[Job] = []
        self.total_response_times: List[float] = []

    def handle_event(self, event: Event) -> None:
        """Lưu lại job hoàn thành, tính trễ toàn trình và giải phóng Future tương ứng (nếu có)."""
        super().handle_event(event)
        etype = str(event.event_type).upper()
        if etype in ("ARRIVAL", "EVENTTYPE.ARRIVAL", "DEPARTURE", "EVENTTYPE.DEPARTURE"):
            payload = event.payload if isinstance(event.payload, dict) else {}
            job: Optional[Job] = payload.get("job")
            if job:
                # 1. Ghi nhận thời gian phản hồi toàn trình (Response time = departure - orig_arrival)
                self.completed_jobs.append(job)
                resp = event.timestamp - job.orig_arrival_time
                self.total_response_times.append(resp)
                # 2. Giải phóng Future bất đồng bộ nếu có coroutine đang await kết quả
                if self.future_manager is not None and hasattr(self.future_manager, "has_pending"):
                    if self.future_manager.has_pending(job.job_id):
                        self.future_manager.set_result(job.job_id, job)

    @property
    def total_completed(self) -> int:
        """Tổng số lượng job đã hoàn thành xử lý và tới Sink."""
        return len(self.completed_jobs)

    def get_metrics(self) -> Dict[str, Any]:
        """Tính thời gian phản hồi trung bình (mean response time) toàn trình."""
        avg_resp = (
            sum(self.total_response_times) / len(self.total_response_times)
            if self.total_response_times else 0.0
        )
        return {
            "total_completed": len(self.completed_jobs),
            "completed_jobs": len(self.completed_jobs),
            "mean_response_time": avg_resp,
        }

    def reset(self) -> None:
        """Xóa danh sách job và thời gian phản hồi."""
        super().reset()
        self.completed_jobs.clear()
        self.total_response_times.clear()
