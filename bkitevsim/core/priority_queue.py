"""Priority Queue implementations for Discrete Event Simulation.

Cung cấp MinHeapPriorityQueue O(log N) và LadderQueue O(1)
phân tầng duy trì thứ tự sự kiện theo timestamp.
"""

from __future__ import annotations
import heapq
from typing import List, Optional
from bkitevsim.core.event import Event


class BaseEventQueue:
    """Giao diện cơ sở cho các hàng đợi sự kiện ưu tiên."""

    def push(self, event: Event) -> None:
        """Đẩy sự kiện vào hàng đợi."""
        raise NotImplementedError

    def pop(self) -> Event:
        """Lấy sự kiện có timestamp nhỏ nhất ra khỏi hàng đợi."""
        raise NotImplementedError

    def peek(self) -> Optional[Event]:
        """Xem trước sự kiện sớm nhất mà không xóa khỏi hàng đợi."""
        raise NotImplementedError

    def __len__(self) -> int:
        """Trả về tổng số sự kiện đang chờ trong hàng đợi."""
        raise NotImplementedError

    def is_empty(self) -> bool:
        """Kiểm tra hàng đợi có rỗng hay không."""
        return len(self) == 0


class MinHeapPriorityQueue(BaseEventQueue):
    """Hàng đợi nhị phân Min-Heap chuẩn sử dụng heapq của Python."""

    def __init__(self) -> None:
        self._heap: List[Event] = []

    def push(self, event: Event) -> None:
        """Thêm sự kiện vào min-heap với độ phức tạp O(log N)."""
        heapq.heappush(self._heap, event)

    def pop(self) -> Event:
        """Rút sự kiện sớm nhất ra khỏi heap với độ phức tạp O(log N)."""
        if not self._heap:
            raise IndexError("pop from empty event queue")
        return heapq.heappop(self._heap)

    def peek(self) -> Optional[Event]:
        """Xem phần tử gốc min của heap O(1)."""
        return self._heap[0] if self._heap else None

    def __len__(self) -> int:
        return len(self._heap)


class LadderQueue(BaseEventQueue):
    """Hàng đợi phân tầng LadderQueue đạt độ phức tạp O(1) amortized.

    Cấu trúc phân tầng:
    - _bottom: Bộ đệm chứa các sự kiện sắp diễn ra ngay (timestamp <= _boundary).
    - _top: Kho chứa các sự kiện tương lai xa hơn (timestamp > _boundary).
    - Cơ chế nạp định kỳ (_refill_bottom) chuyển các bucket kế tiếp xuống bottom.
    """

    def __init__(self, bucket_width: float = 1.0, rung_width: Optional[float] = None) -> None:
        self.bucket_width = rung_width if rung_width is not None else bucket_width
        self.rung_width = self.bucket_width
        self._bottom: List[Event] = []
        self._top: List[Event] = []
        self._boundary: float = -1.0
        self._count: int = 0

    def push(self, event: Event) -> None:
        """Phân loại và đẩy sự kiện vào tầng _bottom hoặc _top tùy theo mốc boundary."""
        self._count += 1
        if not self._bottom:
            if not self._top:
                self._boundary = event.timestamp + self.bucket_width
                heapq.heappush(self._bottom, event)
                return
            else:
                if event.timestamp <= self._boundary:
                    heapq.heappush(self._bottom, event)
                else:
                    heapq.heappush(self._top, event)
        else:
            if event.timestamp <= self._boundary:
                heapq.heappush(self._bottom, event)
            else:
                heapq.heappush(self._top, event)

    def pop(self) -> Event:
        """Lấy sự kiện sớm nhất từ _bottom; tự động nạp từ _top khi _bottom cạn."""
        if self._count == 0:
            raise IndexError("pop from empty LadderQueue")

        if not self._bottom:
            self._refill_bottom()

        event = heapq.heappop(self._bottom)
        self._count -= 1
        return event

    def peek(self) -> Optional[Event]:
        """Xem trước sự kiện sớm nhất từ tầng _bottom."""
        if self._count == 0:
            return None
        if not self._bottom:
            self._refill_bottom()
        return self._bottom[0] if self._bottom else None

    def _refill_bottom(self) -> None:
        """Nạp tầng _bottom từ các sự kiện trong khoảng bucket kế tiếp ở tầng _top."""
        if not self._top:
            return

        min_future_time = self._top[0].timestamp
        self._boundary = min_future_time + self.bucket_width

        remaining_top: List[Event] = []
        for ev in self._top:
            if ev.timestamp <= self._boundary:
                self._bottom.append(ev)
            else:
                remaining_top.append(ev)

        heapq.heapify(self._bottom)
        self._top = remaining_top
        heapq.heapify(self._top)

    def __len__(self) -> int:
        return self._count
