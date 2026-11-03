import asyncio
import pytest
from bkitevsim.async_engine.future_manager import AsyncFutureManager
from bkitevsim.async_engine.task_coordinator import AsyncTaskCoordinator
from bkitevsim.core.event import Event, EventType
from bkitevsim.models.single_queue import Job, SinkLP


def test_future_manager_create_and_resolve():
    """Kiểm thử chu trình sống của Future: tạo future, await không nghẽn, và hoàn tất."""
    async def run_test():
        fm = AsyncFutureManager()
        req_id = 101

        future = fm.create_future(req_id)
        assert fm.has_pending(req_id) is True
        assert fm.pending_count() == 1
        assert not future.done()

        # Kích hoạt hoàn tất lời hứa
        dummy_job = Job(job_id=req_id, arrival_time=1.5)
        success = fm.set_result(req_id, dummy_job)

        assert success is True
        assert future.done() is True
        result = await future
        assert result.job_id == 101
        assert fm.pending_count() == 0

    asyncio.run(run_test())


def test_task_coordinator_gather():
    """Listing 2a: Kiểm thử gom nhóm kết quả song hành với asyncio.gather."""
    async def sample_op(x: int) -> int:
        await asyncio.sleep(0.01)
        return x * 2

    async def run_test():
        coros = [sample_op(1), sample_op(2), sample_op(3)]
        results = await AsyncTaskCoordinator.run_with_gather(coros)
        assert results == [2, 4, 6]

    asyncio.run(run_test())


def test_task_coordinator_task_group():
    """Listing 2b: Kiểm thử Structured Concurrency với asyncio.TaskGroup."""
    async def sample_task(val: str) -> str:
        await asyncio.sleep(0.01)
        return f"done_{val}"

    async def run_test():
        coros = [sample_task("A"), sample_task("B")]
        results = await AsyncTaskCoordinator.run_with_task_group(coros)
        assert results == ["done_A", "done_B"]

    asyncio.run(run_test())


def test_task_coordinator_as_completed():
    """Listing 2c: Kiểm thử tiêu thụ kết quả FCFS (ai xong trước nhận trước)."""
    async def fast_op() -> str:
        await asyncio.sleep(0.01)
        return "fast"

    async def slow_op() -> str:
        await asyncio.sleep(0.03)
        return "slow"

    async def run_test():
        received_order = []
        def callback(res: str) -> None:
            received_order.append(res)

        results = await AsyncTaskCoordinator.process_as_completed(
            [slow_op(), fast_op()],
            callback=callback
        )
        assert received_order[0] == "fast"
        assert "slow" in results and "fast" in results

    asyncio.run(run_test())


def test_task_coordinator_runner():
    """Listing 3a(bis): Kiểm thử asyncio.Runner độc lập tự dọn dẹp tài nguyên."""
    async def main_coro() -> int:
        await asyncio.sleep(0.01)
        return 999

    res = AsyncTaskCoordinator.run_in_runner(main_coro())
    assert res == 999


def test_sink_lp_resolves_future():
    """Kiểm thử tích hợp: SinkLP tự động resolve Future trong AsyncFutureManager khi Job chạm đích."""
    fm = AsyncFutureManager()
    sink = SinkLP(lp_id="Sink", future_manager=fm)

    # Đăng ký future cho Job 202
    job_id = 202
    future = fm.create_future(job_id)
    assert fm.has_pending(job_id) is True

    # Tạo sự kiện Job 202 đi tới Sink
    job = Job(job_id=job_id, arrival_time=5.0)
    event = Event(
        timestamp=10.0,
        event_type=EventType.DEPARTURE,
        source_lp="Server",
        dest_lp="Sink",
        payload={"job": job}
    )

    sink.handle_event(event)

    # Future phải được resolve ngay
    assert future.done() is True
    assert future.result() == job
    assert fm.has_pending(job_id) is False


def test_future_manager_exception_and_cancellation():
    """Kiểm thử cơ chế bẫy lỗi (set_exception) và hủy toàn bộ Future (cancel_all)."""
    async def run_test():
        fm = AsyncFutureManager()

        # 1. Test set_exception
        req_err = 301
        fut_err = fm.create_future(req_err)
        fm.set_exception(req_err, ValueError("Simulation node failed"))

        assert fut_err.done() is True
        with pytest.raises(ValueError, match="Simulation node failed"):
            await fut_err
        assert fm.has_pending(req_err) is False

        # 2. Test cancel_all
        fut1 = fm.create_future(401)
        fut2 = fm.create_future(402)
        assert fm.pending_count() == 2

        fm.cancel_all()
        assert fm.pending_count() == 0
        assert fut1.cancelled() is True
        assert fut2.cancelled() is True

    asyncio.run(run_test())


def test_future_manager_timeout_handling():
    """Kiểm thử xử lý timeout khi yêu cầu mô phỏng vượt quá thời hạn chờ."""
    async def run_test():
        fm = AsyncFutureManager()
        req_id = 501
        fut = fm.create_future(req_id)

        # Giả lập người dùng chờ tối đa 0.05s nhưng mô phỏng chưa hoàn thành
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(fut, timeout=0.03)

        # Future vẫn ở trạng thái pending trong manager cho đến khi cancel hoặc dọn dẹp
        assert fm.has_pending(req_id) is True
        fm.cancel_all()
        assert fm.has_pending(req_id) is False

    asyncio.run(run_test())

