"""Sequential and Distributed Sequential Event Dispatchers for PDES.

SequentialEventDispatcher xử lý sự kiện tuần tự theo thứ tự thời gian nghiêm ngặt.
DistributedEventDispatcher phân chia hàng đợi theo từng LP để mô phỏng phân tán.
"""

from __future__ import annotations
import math
import time
from typing import Any, Dict, List, Optional
from bkitevsim.core.event import Event
from bkitevsim.core.logical_process import BkSysLogicalProcess
from bkitevsim.core.priority_queue import LadderQueue


class SequentialEventDispatcher:
    """Bộ điều phối sự kiện tuần tự (Single-threaded Event Dispatcher).

    Rút và xử lý sự kiện từ hàng đợi ưu tiên tập trung (LadderQueue)
    đảm bảo tính đơn điệu của đồng hồ mô phỏng (ti <= ti+1).
    """

    def __init__(
        self,
        end_time: float = math.inf,
        bucket_width: float = 1.0,
        event_queue: Optional[Any] = None,
        use_ladder_queue: bool = True,
        **kwargs: Any
    ) -> None:
        self.end_time: float = end_time
        self.bucket_width: float = bucket_width
        self.lps: Dict[Any, BkSysLogicalProcess] = {}
        if event_queue is not None:
            self.event_queue = event_queue
        elif use_ladder_queue:
            self.event_queue = LadderQueue(bucket_width=bucket_width)
        else:
            from bkitevsim.core.priority_queue import MinHeapPriorityQueue
            self.event_queue = MinHeapPriorityQueue()
        self.current_time: float = 0.0
        self.events_processed: int = 0
        self.trace_log: List[Dict[str, Any]] = []
        self.max_trace_entries: int = 1000
        self.stats: Dict[str, Any] = {}
        self._initialized: bool = False

    def register_lp(self, lp: BkSysLogicalProcess) -> None:
        """Đăng ký một Tiến trình Logic (LP) vào bộ điều phối."""
        if lp.lp_id in self.lps:
            raise ValueError(f"LP with id {lp.lp_id} is already registered.")
        lp.dispatcher = self
        self.lps[lp.lp_id] = lp

    def get_lp(self, lp_id: Any) -> Optional[BkSysLogicalProcess]:
        """Lấy tham chiếu tới LP theo ID định danh."""
        return self.lps.get(lp_id)

    def get_all_lps(self) -> List[BkSysLogicalProcess]:
        """Lấy toàn bộ danh sách các LP đã đăng ký."""
        return list(self.lps.values())

    def schedule_event(self, event: Event) -> None:
        """Đẩy một sự kiện mới vào hàng đợi sự kiện tập trung."""
        self.event_queue.push(event)

    def schedule_initial_events(self) -> None:
        """Gọi hàm initialize() của mọi LP để kích hoạt sự kiện ban đầu."""
        if self._initialized:
            return
        self._initialized = True
        for lp in self.lps.values():
            lp.initialize()
            for ev in lp.get_output_events():
                self.schedule_event(ev)

    def run(self, end_time: Optional[float] = None) -> Dict[str, Any]:
        """Vòng lặp chính: rút sự kiện sớm nhất và chuyển tới LP nhận xử lý."""
        if end_time is not None:
            self.end_time = float(end_time)
        wall_start = time.perf_counter()
        self.schedule_initial_events()

        while not self.event_queue.is_empty():
            event = self.event_queue.pop()

            if event.timestamp > self.end_time:
                # Đẩy trả lại sự kiện vượt mốc và dừng mô phỏng
                self.event_queue.push(event)
                break

            self.current_time = event.timestamp

            if len(self.trace_log) < self.max_trace_entries:
                self.trace_log.append({
                    "seq": self.events_processed + 1,
                    "event_id": event.event_id,
                    "timestamp": event.timestamp,
                    "type": str(event.event_type),
                    "src": event.sender_id,
                    "dst": event.receiver_id
                })

            receiver = self.lps.get(event.receiver_id)
            if receiver is not None:
                receiver.set_local_virt_time(event.timestamp)
                receiver.handle_event(event)
                for ev in receiver.get_output_events():
                    self.schedule_event(ev)

            self.events_processed += 1

        for lp in self.lps.values():
            lp.finalize()

        wall_duration = time.perf_counter() - wall_start
        self.stats = {
            "simulation_time": self.current_time,
            "events_processed": self.events_processed,
            "wall_time": wall_duration,
            "end_time": self.end_time,
            "dispatcher": "sequential",
        }
        return self.stats

    def __repr__(self) -> str:
        return (
            f"SequentialEventDispatcher(current_time={self.current_time:.4f}, "
            f"events_processed={self.events_processed}, lps={len(self.lps)})"
        )


class DistributedEventDispatcher(SequentialEventDispatcher):
    """Bộ điều phối phân vùng: mỗi LP sở hữu một hàng đợi LadderQueue cục bộ riêng."""

    def __init__(self, end_time: float = math.inf, bucket_width: float = 1.0) -> None:
        super().__init__(end_time=end_time, bucket_width=bucket_width)
        self._lp_queues: Dict[Any, LadderQueue] = {}

    def register_lp(self, lp: BkSysLogicalProcess) -> None:
        """Đăng ký LP và cấp phát một hàng đợi LadderQueue độc lập cho LP đó."""
        super().register_lp(lp)
        self._lp_queues[lp.lp_id] = LadderQueue(bucket_width=self.bucket_width)

    def schedule_event(self, event: Event) -> None:
        """Đẩy sự kiện thẳng vào hàng đợi cục bộ của LP nhận."""
        dest = event.receiver_id
        if dest not in self._lp_queues:
            self._lp_queues[dest] = LadderQueue(bucket_width=self.bucket_width)
        self._lp_queues[dest].push(event)

    def run(self, end_time: Optional[float] = None) -> Dict[str, Any]:
        """Chọn LP có sự kiện kế tiếp sớm nhất trên toàn bộ các hàng đợi cục bộ để thực thi."""
        if end_time is not None:
            self.end_time = float(end_time)
        wall_start = time.perf_counter()
        self.schedule_initial_events()

        while True:
            min_timestamp = math.inf
            min_lp_id = None

            for lp_id, q in self._lp_queues.items():
                if not q.is_empty():
                    peek_ev = q.peek()
                    if peek_ev is not None and peek_ev.timestamp < min_timestamp:
                        min_timestamp = peek_ev.timestamp
                        min_lp_id = lp_id

            if min_lp_id is None:
                break

            if min_timestamp > self.end_time:
                break

            event = self._lp_queues[min_lp_id].pop()
            self.current_time = event.timestamp

            if len(self.trace_log) < self.max_trace_entries:
                self.trace_log.append({
                    "seq": self.events_processed + 1,
                    "event_id": event.event_id,
                    "timestamp": event.timestamp,
                    "type": str(event.event_type),
                    "src": event.sender_id,
                    "dst": event.receiver_id
                })

            receiver = self.lps.get(event.receiver_id)
            if receiver is not None:
                receiver.set_local_virt_time(event.timestamp)
                receiver.handle_event(event)
                for ev in receiver.get_output_events():
                    self.schedule_event(ev)

            self.events_processed += 1

        for lp in self.lps.values():
            lp.finalize()

        wall_duration = time.perf_counter() - wall_start
        self.stats = {
            "simulation_time": self.current_time,
            "events_processed": self.events_processed,
            "wall_time": wall_duration,
            "end_time": self.end_time,
            "dispatcher": "distributed_sequential",
        }
        return self.stats
