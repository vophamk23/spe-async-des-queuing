"""Coroutine-based Logical Process and Event Loop for bkitevsim.

Cung cấp BkSysCoEventLoop, BkSysCoLogicalProcess, BkSysFuture và BkSysCoLPStatus.
Cho phép mô phỏng sự kiện rời rạc bằng cú pháp bất đồng bộ async/await.
"""

from __future__ import annotations
import asyncio
import enum
import math
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional
from bkitevsim.core.event import Event
from bkitevsim.core.logical_process import BkSysLogicalProcess, BkSysLogicalProcessState
from bkitevsim.core.priority_queue import LadderQueue


class BkSysCoLPStatus(enum.Enum):
    """Trạng thái vòng đời của một Coroutine Logical Process (CoLP)."""
    READY = "ready"                    # Sẵn sàng chạy
    WAITING_EVENT = "waiting_event"    # Đang tạm dừng chờ sự kiện
    WAITING_TIME = "waiting_time"      # Đang tạm dừng chờ đồng hồ ảo
    SUSPENDED = "suspended"            # Bị treo tạm thời
    TERMINATED = "terminated"          # Đã hoàn tất


class BkSysFuture(asyncio.Future):
    """Lớp Future mở rộng kế thừa asyncio.Future phục vụ PDES."""

    def is_pending(self) -> bool:
        """Kiểm tra future có đang chờ xử lý hay không."""
        return not self.done()

    def is_resolved(self) -> bool:
        """Kiểm tra future đã được giải phóng thành công (có kết quả)."""
        return self.done() and not self.cancelled() and self.exception() is None

    def is_rejected(self) -> bool:
        """Kiểm tra future kết thúc do lỗi ngoại lệ."""
        return self.done() and not self.cancelled() and self.exception() is not None

    def is_cancelled(self) -> bool:
        """Kiểm tra future đã bị hủy."""
        return self.cancelled()

    def add_error_callback(self, fn: Callable[[BaseException], None]) -> None:
        """Đăng ký callback gọi khi future gặp lỗi ngoại lệ."""
        def _on_done(fut: asyncio.Future) -> None:
            if fut.done() and not fut.cancelled() and fut.exception() is not None:
                fn(fut.exception())
        self.add_done_callback(_on_done)

    def add_cancel_callback(self, fn: Callable[[], None]) -> None:
        """Đăng ký callback gọi khi future bị hủy bỏ."""
        def _on_done(fut: asyncio.Future) -> None:
            if fut.cancelled():
                fn()
        self.add_done_callback(_on_done)


class BkSysCoLogicalProcess(BkSysLogicalProcess):
    """Lớp cơ sở cho các tiến trình logic chạy dưới dạng Coroutine.

    Hỗ trợ cú pháp bất đồng bộ:
    - await self.wait_for(event_type): Tạm dừng chờ sự kiện mong muốn.
    - await self.advance_time(delta): Nhường quyền và tiến đồng hồ ảo thêm delta.
    """

    def __init__(
        self,
        lp_id: int | str,
        initial_state: Optional[BkSysLogicalProcessState] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(lp_id=lp_id, initial_state=initial_state)
        self._event_loop: Optional[BkSysCoEventLoop] = None
        self._lookahead: float = float(kwargs.get("lookahead", 0.0))
        self._status: BkSysCoLPStatus = BkSysCoLPStatus.READY
        self._event_buffer: List[Event] = []                        # Bộ đệm sự kiện đến sớm
        self._waiters: Dict[str, List[asyncio.Future]] = {}         # Danh sách Future chờ sự kiện
        self._time_waiters: List[tuple[float, asyncio.Future]] = [] # Danh sách Future chờ mốc thời gian

    def set_event_loop(self, event_loop: BkSysCoEventLoop) -> None:
        """Gắn tham chiếu tới CoEventLoop điều phối."""
        self._event_loop = event_loop
        self._dispatcher = event_loop

    def handle_event(self, event: Event) -> None:
        """Tiếp nhận sự kiện và đánh thức coroutine đang 'await wait_for' phù hợp."""
        etype = str(event.event_type)
        # Nếu có coroutine đang chờ loại sự kiện này -> giải phóng future ngay
        if etype in self._waiters and self._waiters[etype]:
            fut = self._waiters[etype].pop(0)
            if not fut.done():
                fut.set_result(event)
        else:
            # Ngược lại lưu vào bộ đệm để chờ coroutine gọi wait_for sau
            self._event_buffer.append(event)

    async def wait_for(self, event_type: str, timeout: Optional[float] = None) -> Event:
        """Tạm dừng coroutine cho tới khi nhận đúng loại sự kiện event_type."""
        etype = str(event_type)
        # 1. Kiểm tra sự kiện đã nằm sẵn trong bộ đệm chưa
        for i, ev in enumerate(self._event_buffer):
            if str(ev.event_type) == etype:
                return self._event_buffer.pop(i)

        if self._event_loop is None:
            raise RuntimeError("Event loop is not set on BkSysCoLogicalProcess.")

        # 2. Tạo Future mới và treo coroutine vào hàng đợi chờ
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        if etype not in self._waiters:
            self._waiters[etype] = []
        self._waiters[etype].append(fut)

        # 3. Chuyển trạng thái sang chờ sự kiện
        self._status = BkSysCoLPStatus.WAITING_EVENT
        try:
            if timeout is not None:
                return await asyncio.wait_for(fut, timeout=timeout)
            return await fut
        finally:
            # 4. Khi được đánh thức, chuyển trạng thái về READY và dọn sạch waiter
            self._status = BkSysCoLPStatus.READY
            if etype in self._waiters and fut in self._waiters[etype]:
                self._waiters[etype].remove(fut)

    async def wait_for_multiple(self, event_types: List[str], timeout: Optional[float] = None) -> Event:
        """Tạm dừng chờ bất kỳ sự kiện nào trong danh sách event_types đến trước."""
        types_set = {str(t) for t in event_types}
        # 1. Kiểm tra bộ đệm
        for i, ev in enumerate(self._event_buffer):
            if str(ev.event_type) in types_set:
                return self._event_buffer.pop(i)

        # 2. Tạo Future dùng chung cho tất cả các loại sự kiện cần chờ
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        for etype in types_set:
            if etype not in self._waiters:
                self._waiters[etype] = []
            self._waiters[etype].append(fut)

        self._status = BkSysCoLPStatus.WAITING_EVENT
        try:
            if timeout is not None:
                return await asyncio.wait_for(fut, timeout=timeout)
            return await fut
        finally:
            self._status = BkSysCoLPStatus.READY
            for etype in types_set:
                if etype in self._waiters and fut in self._waiters[etype]:
                    self._waiters[etype].remove(fut)

    async def wait_until(self, target_time: float) -> float:
        """Tạm dừng chờ đồng hồ ảo hệ thống đạt tới mốc target_time."""
        if self._event_loop is None:
            raise RuntimeError("Event loop is not set on BkSysCoLogicalProcess.")
        return await self._event_loop.wait_until_time(self.lp_id, target_time)

    async def advance_time(self, delta: float) -> float:
        """Nhường quyền điều khiển và đợi thời gian ảo trôi thêm delta."""
        if self._event_loop is None:
            raise RuntimeError("Event loop is not set on BkSysCoLogicalProcess.")
        return await self._event_loop.advance_time(self.lp_id, delta)

    def send_event(self, event: Event) -> None:
        """Gửi sự kiện qua CoEventLoop."""
        super().send_event(event)
        if self._event_loop is not None:
            self._event_loop.schedule_event(event)

    async def coroutine_run(self) -> None:
        """Coroutine chính do lớp con hiện thực hành vi nghiệp vụ."""
        pass


class BkSysCoEventLoop:
    """Vòng lặp sự kiện bất đồng bộ điều phối các CoLP hợp tác."""

    def __init__(self, end_time: float = math.inf, bucket_width: float = 1.0) -> None:
        self.end_time: float = end_time
        self.bucket_width: float = bucket_width
        self.current_time: float = 0.0
        self.event_queue: LadderQueue = LadderQueue(bucket_width=bucket_width) # Hàng đợi O(1)
        self.lps: Dict[Any, BkSysCoLogicalProcess] = {}
        self.stats: Dict[str, Any] = {}
        self._running: bool = False
        self._time_waiters: List[tuple[float, asyncio.Future]] = []           # Danh sách hẹn giờ thức giấc
        self.events_processed: int = 0

    def register_lp(self, lp: BkSysCoLogicalProcess) -> None:
        """Đăng ký một CoLP vào vòng lặp sự kiện bất đồng bộ."""
        if lp.lp_id in self.lps:
            raise ValueError(f"LP with id {lp.lp_id} is already registered.")
        lp.set_event_loop(self)
        self.lps[lp.lp_id] = lp

    def schedule_event(self, event: Event) -> None:
        """Lập lịch gửi sự kiện vào hàng đợi LadderQueue."""
        self.event_queue.push(event)

    def schedule_event_at(self, timestamp: float, event: Event) -> None:
        """Lập lịch gửi sự kiện tại mốc thời gian timestamp cụ thể."""
        event.timestamp = timestamp
        self.schedule_event(event)

    def create_future(self) -> BkSysFuture:
        """Tạo một BkSysFuture gắn với event loop hiện tại."""
        loop = asyncio.get_running_loop()
        return BkSysFuture(loop=loop)

    async def advance_time(self, lp_id: Any, delta: float) -> float:
        """Tiến thời gian ảo thêm delta và tạm dừng coroutine của LP."""
        target_time = self.current_time + delta
        return await self.wait_until_time(lp_id, target_time)

    async def wait_until_time(self, lp_id: Any, target_time: float) -> float:
        """Chờ thời gian ảo đạt tới target_time bằng Future và sự kiện thức giấc."""
        if self.current_time >= target_time:
            return self.current_time

        # 1. Tạo Future hẹn giờ cho coroutine
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._time_waiters.append((target_time, fut))
        self._time_waiters.sort(key=lambda x: x[0])

        # 2. Đẩy sự kiện giả lập thức giấc vào hàng đợi LadderQueue
        wake_ev = Event(
            timestamp=target_time,
            sender_id=0,
            receiver_id=lp_id if isinstance(lp_id, int) else 0,
            event_type="__WAKE_TIME__"
        )
        self.event_queue.push(wake_ev)
        return await fut

    def run(self, end_time: Optional[float] = None) -> Dict[str, Any]:
        """Điểm khởi chạy đồng bộ điều phối CoEventLoop qua asyncio.run()."""
        if end_time is not None:
            self.end_time = float(end_time)

        async def _main_coro() -> Dict[str, Any]:
            return await self._async_run()

        try:
            return asyncio.run(_main_coro())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(_main_coro())

    async def _async_run(self) -> Dict[str, Any]:
        """Vòng lặp bất đồng bộ thực thi song hành các coroutine LP."""
        wall_start = time.perf_counter()
        self._running = True

        # 1. Khởi động task coroutine cho tất cả các LP
        lp_tasks = []
        for lp in self.lps.values():
            lp.initialize()
            for ev in lp.get_output_events():
                self.schedule_event(ev)
            t = asyncio.create_task(lp.coroutine_run())
            lp_tasks.append(t)

        # 2. Vòng lặp rút và xử lý sự kiện
        while not self.event_queue.is_empty() and self._running:
            event = self.event_queue.pop()

            # Dừng nếu vượt quá thời gian mô phỏng
            if event.timestamp > self.end_time:
                self.event_queue.push(event)
                break

            self.current_time = event.timestamp

            # Đánh thức các coroutine đang chờ mốc thời gian ảo này
            while self._time_waiters and self._time_waiters[0][0] <= self.current_time:
                _, w_fut = self._time_waiters.pop(0)
                if not w_fut.done():
                    w_fut.set_result(self.current_time)

            # Chuyển giao sự kiện tới LP nhận
            if str(event.event_type) != "__WAKE_TIME__":
                receiver = self.lps.get(event.receiver_id)
                if receiver is not None:
                    receiver.set_local_virt_time(event.timestamp)
                    receiver.handle_event(event)
                    for ev in receiver.get_output_events():
                        self.schedule_event(ev)

            # Nhường quyền điều khiển (yield control) để coroutine khác chạy
            await asyncio.sleep(0)
            self.events_processed += 1

        # 3. Dọn dẹp và hủy các coroutine còn treo
        self._running = False
        for t in lp_tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*lp_tasks, return_exceptions=True)

        for lp in self.lps.values():
            lp.finalize()

        wall_duration = time.perf_counter() - wall_start
        self.stats = {
            "simulation_time": self.current_time,
            "events_processed": self.events_processed,
            "wall_time": wall_duration,
            "end_time": self.end_time,
            "dispatcher": "coroutine",
        }
        return self.stats
