import asyncio
from typing import Any, Callable, Coroutine, List, Sequence


class AsyncTaskCoordinator:
    """ĐIỀU PHỐI VÀ CHẠY MÔ PHỎNG SONG HÀNH BẤT ĐỒNG BỘ (ASYNCHRONOUS ORCHESTRATION).
    
    Hiện thực đầy đủ 4 kỹ thuật điều phối tác vụ chuẩn trong Python 3.11+ theo Section 4:
    - run_with_task_group: Mô hình đồng quy có cấu trúc (Structured Concurrency) bằng TaskGroup.
    - run_with_gather: Chờ đồng loạt nhiều coroutine cùng lúc.
    - process_as_completed: Tiếp nhận và xử lý kết quả theo thứ tự ai xong trước nhận trước (FCFS).
    - run_in_runner: Chạy tác vụ trong Runner độc lập và tự dọn dẹp tài nguyên.
    """
    @staticmethod
    async def run_with_task_group(coroutines: Sequence[Coroutine[Any, Any, Any]]) -> List[Any]:
        """Listing 2b: Chạy đồng quy có cấu trúc bằng `asyncio.TaskGroup`.
        
        Ưu điểm vượt trội: Nếu 1 task con gặp lỗi ngoại lệ, TaskGroup sẽ tự động
        hủy (cancel) an toàn tất cả các task con còn lại, chống rò rỉ tài nguyên (Task leak).
        """
        tasks = []
        async with asyncio.TaskGroup() as tg:
            for coro in coroutines:
                task = tg.create_task(coro)
                tasks.append(task)
        return [task.result() for task in tasks]

    @staticmethod
    async def run_with_gather(coroutines: Sequence[Coroutine[Any, Any, Any]]) -> List[Any]:
        """Listing 2a: Chạy song hành nhiều coroutine bằng `asyncio.gather` và gom toàn bộ kết quả."""
        return await asyncio.gather(*coroutines)

    @staticmethod
    async def process_as_completed(
        coroutines: Sequence[Coroutine[Any, Any, Any]],
        callback: Callable[[Any], None]
    ) -> List[Any]:
        """Listing 2c: Tiêu thụ kết quả theo thứ tự Đến trước - Phục vụ trước (FCFS).
        
        Mỗi khi có một coroutine hoàn tất, hàm callback sẽ được gọi ngay lập tức
        mà không cần phải đợi các coroutine khác xong.
        """
        results = []
        for finished_task in asyncio.as_completed(coroutines):
            result = await finished_task
            callback(result)
            results.append(result)
        return results

    @staticmethod
    def run_in_runner(main_coro: Coroutine[Any, Any, Any]) -> Any:
        """Listing 3a(bis): Điểm nhập chương trình sử dụng `asyncio.Runner` cô lập.
        
        Tự động khởi tạo event loop, chạy coroutine chính và đóng dọn sạch sẽ khi kết thúc.
        """
        with asyncio.Runner() as runner:
            return runner.run(main_coro)
