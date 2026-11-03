from __future__ import annotations
from enum import Enum, auto


class EventType(Enum):
    """Các loại sự kiện rời rạc cơ bản trong mô hình hàng đợi."""
    ARRIVAL = auto()        # Sự kiện yêu cầu mới đến trạm
    SERVICE_START = auto()  # Sự kiện máy chủ bắt đầu xử lý yêu cầu
    DEPARTURE = auto()      # Sự kiện xử lý xong và rời trạm
    IO_COMPLETE = auto()    # Sự kiện hoàn tất thao tác vào/ra
    MESSAGE = auto()        # Sự kiện trao đổi thông điệp giữa các LP
    TERMINATE = auto()      # Sự kiện báo hiệu dừng mô phỏng


from dataclasses import dataclass, field
import uuid
from typing import Any, Optional


@dataclass(order=True)
class Event:
    """Đại diện cho một thông điệp sự kiện gắn nhãn thời gian giữa các LP.

    Sự kiện được sắp thứ tự ưu tiên tự động theo mốc thời gian timestamp.
    """
    timestamp: float
    sender_id: Any = field(compare=False, default=0)
    receiver_id: Any = field(compare=False, default=0)
    event_type: Any = field(compare=False, default="EVENT")
    payload: Any = field(compare=False, default=None)
    event_id: Any = field(compare=False, default_factory=lambda: str(uuid.uuid4()))

    def __init__(
        self,
        timestamp: float = 0.0,
        sender_id: Any = None,
        receiver_id: Any = None,
        event_type: Any = "EVENT",
        payload: Any = None,
        event_id: Any = None,
        **kwargs: Any
    ) -> None:
        """Khởi tạo sự kiện với timestamp, nguồn gửi, đích nhận và dữ liệu kèm theo."""
        self.timestamp = float(timestamp)
        
        # Xử lý các bí danh cho sender (source_lp, lp_source)
        if sender_id is not None:
            self.sender_id = sender_id
        elif "source_lp" in kwargs:
            self.sender_id = kwargs["source_lp"]
        elif "lp_source" in kwargs:
            self.sender_id = kwargs["lp_source"]
        else:
            self.sender_id = 0

        # Xử lý các bí danh cho receiver (dest_lp, lp_target)
        if receiver_id is not None:
            self.receiver_id = receiver_id
        elif "dest_lp" in kwargs:
            self.receiver_id = kwargs["dest_lp"]
        elif "lp_target" in kwargs:
            self.receiver_id = kwargs["lp_target"]
        else:
            self.receiver_id = 0

        # Chuẩn hóa kiểu sự kiện thành chuỗi
        if hasattr(event_type, "name"):
            self.event_type = event_type.name
        else:
            self.event_type = str(event_type)

        # Xử lý payload/data
        if payload is not None:
            self.payload = payload
        elif "data" in kwargs:
            self.payload = kwargs["data"]
        else:
            self.payload = None

        # Định danh ID sự kiện
        if event_id is not None:
            self.event_id = str(event_id)
        else:
            self.event_id = str(uuid.uuid4())

        self._priority = kwargs.get("priority", 0)

        # Kiểm tra tính hợp lệ của tham số
        if self.timestamp < 0:
            raise ValueError(f"Event timestamp cannot be negative: {self.timestamp}")
        if isinstance(self.sender_id, (int, float)) and self.sender_id < 0:
            raise ValueError(f"Event sender_id cannot be negative: {self.sender_id}")
        if isinstance(self.receiver_id, (int, float)) and self.receiver_id < 0:
            raise ValueError(f"Event receiver_id cannot be negative: {self.receiver_id}")

    def __repr__(self) -> str:
        return (
            f"Event(id={str(self.event_id)[:8]}, t={self.timestamp:.4f}, "
            f"src={self.sender_id}, dst={self.receiver_id}, "
            f"type='{self.event_type}')"
        )

    # Thuộc tính tương thích ngược cho codebase cũ
    @property
    def lp_source(self) -> Any:
        return self.sender_id

    @property
    def lp_target(self) -> Any:
        return self.receiver_id

    @property
    def source_lp(self) -> Any:
        return self.sender_id

    @property
    def dest_lp(self) -> Any:
        return self.receiver_id

    @property
    def data(self) -> Any:
        return self.payload

    @property
    def priority(self) -> int:
        return getattr(self, "_priority", 0)


def create_event(
    timestamp: float,
    sender_id: int | str,
    receiver_id: int | str,
    event_type: str,
    payload: Any = None
) -> Event:
    """Hàm Factory tạo nhanh một đối tượng sự kiện Event chuẩn khung bkitevsim."""
    return Event(
        timestamp=timestamp,
        sender_id=sender_id,
        receiver_id=receiver_id,
        event_type=str(event_type),
        payload=payload
    )
