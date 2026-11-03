"""BkSys Logical Process and State classes for PDES.

Định nghĩa lớp cơ sở Tiến trình Logic (BkSysLogicalProcess) và
Trạng thái tiến trình (BkSysLogicalProcessState) chuẩn khung bkitevsim.
"""

from __future__ import annotations
import abc
import copy
from typing import Any, Callable, Dict, List, Optional
from bkitevsim.core.event import Event


class BkSysLogicalProcessState:
    """Quản lý trạng thái động của LP; hỗ trợ checkpoint và khôi phục trạng thái (PDES)."""

    def __init__(self, **kwargs: Any) -> None:
        self._data: Dict[str, Any] = dict(kwargs)
        self.history: List[Dict[str, Any]] = []

    def get(self, key: str, default: Any = None) -> Any:
        """Lấy giá trị thuộc tính trạng thái theo key."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Gán giá trị mới cho thuộc tính trạng thái."""
        self._data[key] = value

    def checkpoint(self) -> Dict[str, Any]:
        """Tạo bản sao sâu (deep-copy) lưu giữ snapshot trạng thái hiện tại."""
        return copy.deepcopy(self._data)

    def restore(self, checkpoint: Dict[str, Any]) -> None:
        """Khôi phục trạng thái LP về bản sao lưu checkpoint trước đó."""
        self._data = copy.deepcopy(checkpoint)

    def copy(self) -> BkSysLogicalProcessState:
        """Nhân bản đối tượng trạng thái kèm toàn bộ lịch sử biến đổi."""
        new_state = BkSysLogicalProcessState(**copy.deepcopy(self._data))
        new_state.history = copy.deepcopy(self.history)
        return new_state

    def record_step(self, timestamp: float, description: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Ghi vết một bước chuyển trạng thái phục vụ kiểm chứng và truy vết."""
        self.history.append({
            "timestamp": timestamp,
            "description": description,
            "data": data or {}
        })

    def __getattr__(self, name: str) -> Any:
        if name in ("_data", "history"):
            return super().__getattribute__(name)
        if name in self._data:
            return self._data[name]
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("_data", "history"):
            super().__setattr__(name, value)
        else:
            self._data[name] = value


class BkSysLogicalProcess(abc.ABC):
    """Lớp cơ sở trừu tượng cho mọi Tiến trình Logic (LP) trong hệ thống mô phỏng DES.

    Mỗi LP đại diện cho một trạm/thành phần, có ID định danh và đồng hồ ảo cục bộ (LVT).
    """

    def __init__(
        self,
        lp_id: int | str,
        initial_state: Optional[BkSysLogicalProcessState] = None
    ) -> None:
        self.lp_id = lp_id
        self.local_virt_time: float = 0.0
        self.state: BkSysLogicalProcessState = (
            initial_state if initial_state is not None else BkSysLogicalProcessState()
        )
        self._output_events: List[Event] = []
        self._dispatcher: Optional[Any] = None
        self._handlers: Dict[str, Callable[[Event], None]] = {}

    @property
    def dispatcher(self) -> Optional[Any]:
        return self._dispatcher

    @dispatcher.setter
    def dispatcher(self, d: Any) -> None:
        self._dispatcher = d

    # Bí danh tương thích ngược cho local_virtual_time
    @property
    def local_virtual_time(self) -> float:
        return self.local_virt_time

    @local_virtual_time.setter
    def local_virtual_time(self, val: float) -> None:
        self.set_local_virt_time(val)

    def initialize(self) -> None:
        """Khởi tạo LP và lập lịch các sự kiện ban đầu trước khi mô phỏng chạy."""
        pass

    def finalize(self) -> None:
        """Dọn dẹp và tổng kết chỉ số đo đạc khi mô phỏng kết thúc."""
        pass

    def get_local_virt_time(self) -> float:
        """Lấy giá trị thời gian ảo cục bộ (LVT) hiện tại của LP."""
        return self.local_virt_time

    def set_local_virt_time(self, local_virt_time: float) -> None:
        """Cập nhật LVT; kiểm tra điều kiện nhân quả (cấm lùi thời gian ảo)."""
        if local_virt_time < self.local_virt_time:
            raise ValueError(
                f"Causality violation in LP {self.lp_id}: cannot travel backward "
                f"from {self.local_virt_time:.4f} to {local_virt_time:.4f}"
            )
        self.local_virt_time = local_virt_time

    def elapse_virt_time(self, delta: float) -> float:
        """Tăng thời gian ảo cục bộ thêm một khoảng delta không âm (delta >= 0)."""
        if delta < 0:
            raise ValueError(f"Time delta cannot be negative: {delta}")
        self.local_virt_time += delta
        return self.local_virt_time

    def register_handler(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Đăng ký hàm callback xử lý riêng cho một loại sự kiện cụ thể."""
        self._handlers[str(event_type)] = handler

    def send_event(self, event: Event) -> None:
        """Gửi sự kiện đến Dispatcher lập lịch hoặc đệm vào hàng ra."""
        if self._dispatcher is not None and hasattr(self._dispatcher, "schedule_event"):
            self._dispatcher.schedule_event(event)
        else:
            self._output_events.append(event)

    def schedule_event(self, event: Event) -> None:
        """Bí danh tương thích: lập lịch sự kiện trực tiếp qua Dispatcher."""
        self.send_event(event)

    def get_output_events(self) -> List[Event]:
        """Thu gom và làm rỗng danh sách các sự kiện vừa được phát sinh."""
        events = self._output_events
        self._output_events = []
        return events

    def handle_event(self, event: Event) -> None:
        """Xử lý sự kiện nhận được bằng cách phân phối tới handler đã đăng ký."""
        handler = self._handlers.get(str(event.event_type))
        if handler:
            handler(event)

    def reset(self) -> None:
        """Đặt lại trạng thái và đồng hồ ảo LP cho phiên mô phỏng mới."""
        self.local_virt_time = 0.0
        self._output_events = []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(lp_id={self.lp_id}, LVT={self.local_virt_time:.4f})"
