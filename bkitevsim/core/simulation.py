"""High-level Simulation controller and configuration options for bkitevsim.

Cung cấp lớp điều khiển cấp cao Simulation Façade và SimulationOptions,
giúp khởi tạo và chạy mô phỏng tinh gọn mà không cần thao tác thủ công từng LP.
"""

from __future__ import annotations
import logging
from typing import Any, Callable, Dict, List, Optional, Type
from bkitevsim.core.logical_process import BkSysLogicalProcess
from bkitevsim.dispatchers.sequential_eventdispatcher import (
    SequentialEventDispatcher,
    DistributedEventDispatcher,
)

logger = logging.getLogger("bkitevsim.core.simulation")


class SimulationOptions:
    """Tập hợp các tham số cấu hình của một phiên mô phỏng (PDES Options)."""

    def __init__(
        self,
        end_time: float = 100.0,
        dispatcher: str = "sequential",
        bucket_width: float = 1.0,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        stats_file: Optional[str] = None,
        verbose: bool = False,
        model_params: Optional[Dict[str, Any]] = None
    ) -> None:
        self.end_time: float = end_time
        self.dispatcher: str = dispatcher
        self.bucket_width: float = bucket_width
        self.log_level: str = log_level
        self.log_file: Optional[str] = log_file
        self.stats_file: Optional[str] = stats_file
        self.verbose: bool = verbose
        self.model_params: Dict[str, Any] = model_params or {}

    def to_dict(self) -> Dict[str, Any]:
        """Xuất cấu hình thành từ điển (dictionary)."""
        return {
            "end_time": self.end_time,
            "dispatcher": self.dispatcher,
            "bucket_width": self.bucket_width,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "stats_file": self.stats_file,
            "verbose": self.verbose,
            "model_params": self.model_params,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SimulationOptions:
        """Tạo đối tượng SimulationOptions từ một từ điển cấu hình."""
        return cls(**data)


class Simulation:
    """Bộ điều khiển cấp cao (Façade Pattern) quản lý trọn vẹn vòng đời mô phỏng."""

    def __init__(
        self,
        options: Optional[SimulationOptions] = None,
        models: Optional[Dict[str, Type[BkSysLogicalProcess]]] = None,
        factories: Optional[Dict[str, Callable[..., BkSysLogicalProcess]]] = None
    ) -> None:
        self.options: SimulationOptions = options if options is not None else SimulationOptions()
        self.models: Dict[str, Type[BkSysLogicalProcess]] = dict(models) if models else {}
        self.factories: Dict[str, Callable[..., BkSysLogicalProcess]] = dict(factories) if factories else {}
        self.lps: Dict[Any, BkSysLogicalProcess] = {}
        self.dispatcher: Optional[SequentialEventDispatcher] = None

    def register_model(self, name: str, model_cls: Type[BkSysLogicalProcess]) -> None:
        """Đăng ký một lớp mô hình LP vào từ điển mô hình của simulation."""
        self.models[name] = model_cls

    def register_factory(self, name: str, factory: Callable[..., BkSysLogicalProcess]) -> None:
        """Đăng ký một hàm factory dùng để tạo LP theo yêu cầu."""
        self.factories[name] = factory

    def create_lp(self, lp_id: int | str, model_name: str, **params: Any) -> BkSysLogicalProcess:
        """Tạo một LP từ tên model hoặc factory đã đăng ký và lưu vào danh sách."""
        if model_name in self.factories:
            lp = self.factories[model_name](lp_id, **params)
        elif model_name in self.models:
            lp = self.models[model_name](lp_id, **params)
        else:
            raise KeyError(f"Unknown model or factory: {model_name}")
        self.lps[lp_id] = lp
        return lp

    def add_lp(self, lp: BkSysLogicalProcess) -> None:
        """Thêm một thực thể LP đã khởi tạo sẵn vào simulation."""
        self.lps[lp.lp_id] = lp

    def build_dispatcher(self) -> SequentialEventDispatcher:
        """Khởi tạo Dispatcher phù hợp với tùy chọn cấu hình và gắn toàn bộ LPs."""
        dtype = self.options.dispatcher.lower()
        if dtype == "distributed_sequential":
            dispatcher = DistributedEventDispatcher(
                end_time=self.options.end_time,
                bucket_width=self.options.bucket_width,
            )
        else:
            dispatcher = SequentialEventDispatcher(
                end_time=self.options.end_time,
                bucket_width=self.options.bucket_width,
            )
        for lp in self.lps.values():
            dispatcher.register_lp(lp)
        self.dispatcher = dispatcher
        return dispatcher

    def run(self) -> Dict[str, Any]:
        """Tự động dựng Dispatcher (nếu chưa có) và điều phối toàn bộ phiên mô phỏng."""
        if self.dispatcher is None:
            self.build_dispatcher()
        return self.dispatcher.run(self.options.end_time)

    def get_stats(self) -> Dict[str, Any]:
        """Lấy từ điển thống kê thực thi từ Dispatcher."""
        if self.dispatcher is not None:
            return self.dispatcher.stats
        return {}
