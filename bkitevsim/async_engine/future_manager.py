import asyncio
from typing import Any, Dict, Optional


class AsyncFutureManager:
    """QUẢN LÝ TÁC VỤ BẤT ĐỒNG BỘ THEO MÔ HÌNH PROMISE / FUTURE (Listing 3 trong đề bài).
    
    Cơ chế hoạt động:
    - Khi một yêu cầu (Request/Job) được gửi vào hệ thống, hàm `create_future(request_id)`
      sẽ tạo ra một đối tượng `asyncio.Future` (lời hứa).
    - Coroutine phía người dùng có thể gọi `await future` để tạm dừng mà KHÔNG LÀM NGHẼN luồng chính.
    - Khi trạm xử lý (SinkLP) hoàn thành công việc, nó gọi `set_result(request_id, job)`
      để hoàn tất lời hứa, tự động đánh thức coroutine đang chờ để nhận kết quả ngay lập tức.
    """
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.loop = loop
        # Lưu trữ các Future đang chờ xử lý: mapping từ request_id -> asyncio.Future
        self._pending_futures: Dict[int, asyncio.Future] = {}

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Lấy Event Loop hiện tại đang chạy hoặc tạo mới an toàn trên Python 3.10+."""
        if self.loop is not None and not self.loop.is_closed():
            return self.loop
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError
                return loop
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self.loop = loop
                return loop

    def create_future(self, request_id: int) -> asyncio.Future:
        """TẠO MỘT FUTURE (LỜI HỨA) GẮN VỚI REQUEST_ID DUY NHẤT."""
        loop = self._get_loop()
        future = loop.create_future()
        self._pending_futures[request_id] = future
        return future

    def set_result(self, request_id: int, result: Any) -> bool:
        """GIẢI PHÓNG LỜI HỨA (FULFILL PROMISE):
        
        Gán kết quả xử lý vào Future và đánh thức coroutine đang 'await'.
        Trả về True nếu giải phóng thành công.
        """
        future = self._pending_futures.pop(request_id, None)
        if future and not future.done():
            future.set_result(result)
            return True
        return False

    def set_exception(self, request_id: int, exception: Exception) -> bool:
        """Báo lỗi vào Future nếu quá trình xử lý gặp sự cố."""
        future = self._pending_futures.pop(request_id, None)
        if future and not future.done():
            future.set_exception(exception)
            return True
        return False

    def cancel_all(self) -> None:
        """Hủy bỏ toàn bộ các Future đang treo khi dừng hệ thống."""
        for fut in self._pending_futures.values():
            if not fut.done():
                fut.cancel()
        self._pending_futures.clear()

    def has_pending(self, request_id: int) -> bool:
        """Kiểm tra xem request_id này có đang chờ kết quả hay không."""
        return request_id in self._pending_futures

    def pending_count(self) -> int:
        """Số lượng request đang nằm chờ giải phóng."""
        return len(self._pending_futures)
