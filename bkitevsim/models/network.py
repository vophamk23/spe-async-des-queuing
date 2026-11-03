"""Queuing Network models (Jackson Network, Tandem & Feedback Networks).

Mô hình mạng hàng đợi đa chặng theo Hình 1 đề bài (hk261_BKsyspeEvsim.pdf):
[Source] -> [IO: mu_io] -> [CPU: mu_cpu] -+-(p=0.3)-> [Printer: mu_printer] -+-> [Sink]
                                          +-(p=0.7)-> [Disk: mu_disk]       -+
"""

from __future__ import annotations
import random
from typing import Any, Dict, List, Optional
from bkitevsim.core.event import Event, create_event
from bkitevsim.models.single_queue import Job, QueueServerLP, SinkLP, SourceLP
from bkitevsim.utils.metrics import MetricsCollector


class BranchingServerLP(QueueServerLP):
    """Trạm máy chủ phân nhánh xác suất: CPU chuyển job sang Printer (30%) hoặc Disk (70%)."""

    def __init__(
        self,
        lp_id: int | str = "CPU",
        printer_lp_id: int | str = "Printer",
        disk_lp_id: int | str = "Disk",
        p_printer: float = 0.3,
        service_rate: float = 5.0,
        num_servers: float = 1,
        capacity: Optional[int] = None,
        metrics: Optional[MetricsCollector] = None
    ) -> None:
        super().__init__(
            lp_id=lp_id,
            dest_lp_id=printer_lp_id,
            service_rate=service_rate,
            num_servers=num_servers,
            capacity=capacity,
            metrics=metrics
        )
        self.printer_lp_id = printer_lp_id
        self.disk_lp_id = disk_lp_id
        self.p_printer = p_printer

    def _handle_departure(self, event: Event) -> None:
        """Hoàn tất xử lý CPU và định tuyến ngẫu nhiên theo xác suất (p_printer vs 1-p_printer)."""
        payload = event.payload if isinstance(event.payload, dict) else {}
        job: Job = payload.get("job")
        service_duration: float = payload.get("duration", 0.0)

        if job and job.start_service_time is not None:
            # 1. Ghi nhận thời gian chờ và hoàn tất phục vụ tại CPU
            wait_time = job.start_service_time - job.arrival_time
            self.metrics.record_completion(wait_time, service_duration)
            job.departure_time = event.timestamp

            # 2. Phân nhánh ngẫu nhiên: 30% sang Printer, 70% sang Disk
            dest = self.printer_lp_id if (random.random() < self.p_printer) else self.disk_lp_id
            # Lưu mốc thời gian vào mạng lần đầu (để tính trễ toàn trình)
            if not hasattr(job, "orig_arrival_time"):
                job.orig_arrival_time = job.arrival_time
            job.arrival_time = event.timestamp

            # 3. Gửi sự kiện ARRIVAL đến trạm kế tiếp (Printer hoặc Disk)
            out_ev = create_event(
                timestamp=event.timestamp,
                sender_id=self.lp_id,
                receiver_id=dest,
                event_type="ARRIVAL",
                payload={"job": job}
            )
            self.send_event(out_ev)

        # 4. Lấy job tiếp theo từ hàng đợi phục vụ tiếp (nếu có)
        if self.waiting_queue:
            next_job = self.waiting_queue.popleft()
            self._start_service(next_job, event.timestamp)
        else:
            # Không còn job -> giảm số máy chủ bận
            self.busy_servers = max(0, self.busy_servers - 1)

        # 5. Cập nhật thống kê trạng thái hàng đợi
        self._notify_state(event.timestamp)


class NetworkSinkLP(SinkLP):
    """Trạm đích mạng hàng đợi: thu thập độ trễ toàn trình từ Source tới Sink."""

    def __init__(self, lp_id: int | str = "Sink") -> None:
        super().__init__(lp_id)
        self.network_latencies: List[float] = []
        self.completed_jobs: List[Job] = []

    def handle_event(self, event: Event) -> None:
        """Ghi nhận job hoàn tất toàn mạng và lưu lại thời gian trễ toàn trình."""
        super().handle_event(event)
        payload = event.payload if isinstance(event.payload, dict) else {}
        job: Optional[Job] = payload.get("job")
        if job:
            # 1. Thu thập job đã hoàn tất qua mạng
            self.completed_jobs.append(job)
            # 2. Tính độ trễ toàn trình = thời điểm ra mạng - thời điểm vào mạng
            orig = getattr(job, "orig_arrival_time", job.arrival_time)
            self.network_latencies.append(event.timestamp - orig)

    def get_metrics(self) -> Dict[str, Any]:
        """Tính độ trễ mạng trung bình (mean network latency) và số job hoàn tất."""
        base = super().get_metrics()
        avg_lat = (
            sum(self.network_latencies) / len(self.network_latencies)
            if self.network_latencies else 0.0
        )
        base["mean_network_latency"] = avg_lat
        base["completed_jobs"] = len(self.completed_jobs)
        return base

    def reset(self) -> None:
        """Đặt lại bộ nhớ đệm độ trễ mạng."""
        super().reset()
        self.network_latencies.clear()
        self.completed_jobs.clear()


class QueuingNetwork:
    """Mạng hàng đợi hoàn chỉnh 4 trạm theo Hình 1 đề bài."""

    def __init__(
        self,
        arrival_rate: float = 2.0,
        mu_io: float = 8.0,
        mu_cpu: float = 10.0,
        mu_printer: float = 4.0,
        mu_disk: float = 6.0,
        p_printer: float = 0.3
    ) -> None:
        self.arrival_rate = arrival_rate
        self.p_printer = p_printer

        self.source = SourceLP(lp_id="Source", dest_lp_id="IO", arrival_rate=arrival_rate)
        self.io = QueueServerLP(lp_id="IO", dest_lp_id="CPU", service_rate=mu_io)
        self.cpu = BranchingServerLP(
            lp_id="CPU",
            printer_lp_id="Printer",
            disk_lp_id="Disk",
            p_printer=p_printer,
            service_rate=mu_cpu
        )
        self.printer = QueueServerLP(lp_id="Printer", dest_lp_id="Sink", service_rate=mu_printer)
        self.disk = QueueServerLP(lp_id="Disk", dest_lp_id="Sink", service_rate=mu_disk)
        self.sink = NetworkSinkLP(lp_id="Sink")

    def register_all(self, dispatcher: Any) -> None:
        """Đăng ký toàn bộ 6 trạm LP vào Dispatcher."""
        dispatcher.register_lp(self.source)
        dispatcher.register_lp(self.io)
        dispatcher.register_lp(self.cpu)
        dispatcher.register_lp(self.printer)
        dispatcher.register_lp(self.disk)
        dispatcher.register_lp(self.sink)

    def start(self) -> None:
        """Khởi động bộ phát sinh lưu lượng Source."""
        self.source.start()

    def get_results(self, sim_time: float = 500.0) -> Dict[str, Any]:
        """Tổng hợp kết quả từng trạm và tự động nhận diện điểm nghẽn cổ chai (Bottleneck)."""
        # 1. Thu thập chỉ số hiệu năng (rho, W, L, Throughput) từng trạm
        io_res = self.io.metrics.finalize(sim_time)
        cpu_res = self.cpu.metrics.finalize(sim_time)
        printer_res = self.printer.metrics.finalize(sim_time)
        disk_res = self.disk.metrics.finalize(sim_time)

        # 2. Tính độ trễ trung bình toàn trình từ Source tới Sink
        avg_network_latency = (
            sum(self.sink.network_latencies) / len(self.sink.network_latencies)
            if self.sink.network_latencies else 0.0
        )

        nodes = {
            "io": io_res,
            "cpu": cpu_res,
            "printer": printer_res,
            "disk": disk_res
        }
        # 3. Tìm nút cổ chai có hệ số sử dụng rho lớn nhất (Bottleneck)
        bottleneck_node = max(nodes.keys(), key=lambda k: nodes[k]["rho"])

        # 4. Trả về kết quả tổng hợp toàn mạng
        return {
            "nodes": nodes,
            "completed_jobs": len(self.sink.completed_jobs),
            "throughput": len(self.sink.completed_jobs) / max(sim_time, 1e-9),
            "avg_end_to_end_latency": avg_network_latency,
            "bottleneck_node": bottleneck_node,
            "bottleneck_rho": nodes[bottleneck_node]["rho"]
        }
