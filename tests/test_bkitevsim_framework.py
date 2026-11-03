"""Comprehensive verification and validation tests for the official bkitevsim framework.

Covers:
1. Simulation & SimulationOptions
2. SequentialEventDispatcher & DistributedEventDispatcher
3. BkSysLogicalProcess lifecycle & state checkpointing
4. BkSysCoEventLoop & BkSysCoLogicalProcess & BkSysFuture
5. End-to-end Kendall queue validation via high-level Simulation Façade
"""

import math
import random
import pytest
from bkitevsim.core.simulation import Simulation, SimulationOptions
from bkitevsim.core.event import Event, create_event
from bkitevsim.core.logical_process import BkSysLogicalProcess, BkSysLogicalProcessState
from bkitevsim.core.logical_coProcess import (
    BkSysCoEventLoop,
    BkSysCoLogicalProcess,
    BkSysFuture,
    BkSysCoLPStatus,
)
from bkitevsim.core.priority_queue import LadderQueue, MinHeapPriorityQueue
from bkitevsim.dispatchers.sequential_eventdispatcher import (
    SequentialEventDispatcher,
    DistributedEventDispatcher,
)
from bkitevsim.models.single_queue import Job, SourceLP, QueueServerLP, SinkLP
from bkitevsim.utils.theory import mm1_theory, mmc_theory
from bkitevsim.utils.metrics import compute_relative_error


def test_simulation_options():
    """Verify SimulationOptions configuration and serialization."""
    opt = SimulationOptions(
        end_time=250.0,
        dispatcher="distributed_sequential",
        bucket_width=0.5,
        log_level="DEBUG"
    )
    assert opt.end_time == 250.0
    assert opt.dispatcher == "distributed_sequential"
    assert opt.bucket_width == 0.5

    d = opt.to_dict()
    assert d["end_time"] == 250.0
    opt2 = SimulationOptions.from_dict(d)
    assert opt2.dispatcher == "distributed_sequential"


def test_event_validation_and_factory():
    """Verify Event creation, validation, and ordering."""
    ev = create_event(timestamp=12.5, sender_id=1, receiver_id=2, event_type="TEST", payload={"k": "v"})
    assert ev.timestamp == 12.5
    assert ev.sender_id == 1
    assert ev.receiver_id == 2
    assert ev.event_type == "TEST"

    with pytest.raises(ValueError):
        create_event(timestamp=-1.0, sender_id=1, receiver_id=2, event_type="BAD")


def test_logical_process_lifecycle():
    """Verify BkSysLogicalProcess lifecycle, LVT monotonicity, and checkpointing."""
    lp = BkSysLogicalProcess(lp_id=10)
    assert lp.get_local_virt_time() == 0.0

    lp.elapse_virt_time(5.5)
    assert lp.get_local_virt_time() == 5.5

    with pytest.raises(ValueError):
        lp.set_local_virt_time(3.0)  # Causality violation

    lp.state.set("counter", 42)
    cp = lp.state.checkpoint()
    lp.state.set("counter", 99)
    assert lp.state.get("counter") == 99
    lp.state.restore(cp)
    assert lp.state.get("counter") == 42


def test_simulation_facade_mm1_sequential():
    """Verify high-level Simulation facade running M/M/1 on SequentialEventDispatcher."""
    random.seed(42)
    lam = 5.0
    mu = 8.0
    theory = mm1_theory(lam, mu)

    opt = SimulationOptions(end_time=5000.0, dispatcher="sequential", bucket_width=1.0)
    sim = Simulation(options=opt)

    source = SourceLP(lp_id="Source", dest_lp_id="Server", arrival_rate=lam)
    server = QueueServerLP(lp_id="Server", dest_lp_id="Sink", service_rate=mu, num_servers=1)
    sink = SinkLP(lp_id="Sink")

    sim.lps["Source"] = source
    sim.lps["Server"] = server
    sim.lps["Sink"] = sink

    stats = sim.run()
    assert stats["events_processed"] > 10000
    assert stats["simulation_time"] <= 5000.0

    metrics = server.get_metrics()
    err_w = compute_relative_error(metrics["W"], theory["W"])
    err_l = compute_relative_error(metrics["L"], theory["L"])
    err_rho = compute_relative_error(metrics["rho"], theory["rho"])

    assert err_w < 5.0, f"M/M/1 Response time error {err_w:.2f}% exceeds 5%"
    assert err_l < 5.0, f"M/M/1 Mean jobs error {err_l:.2f}% exceeds 5%"
    assert err_rho < 5.0, f"M/M/1 Utilization error {err_rho:.2f}% exceeds 5%"


def test_simulation_facade_distributed_dispatcher():
    """Verify DistributedEventDispatcher (partitioned per-LP queues)."""
    random.seed(42)
    opt = SimulationOptions(end_time=500.0, dispatcher="distributed_sequential", bucket_width=1.0)
    sim = Simulation(options=opt)

    source = SourceLP(lp_id="Source", dest_lp_id="Server", arrival_rate=4.0)
    server = QueueServerLP(lp_id="Server", dest_lp_id="Sink", service_rate=6.0, num_servers=1)
    sink = SinkLP(lp_id="Sink")

    sim.lps["Source"] = source
    sim.lps["Server"] = server
    sim.lps["Sink"] = sink

    stats = sim.run()
    assert stats["dispatcher"] == "distributed_sequential"
    assert stats["events_processed"] > 1000
    assert sink.total_completed > 1000


def test_coroutine_logical_process_and_event_loop():
    """Verify BkSysCoEventLoop and BkSysCoLogicalProcess async coroutines."""
    class WorkerCoLP(BkSysCoLogicalProcess):
        def __init__(self, lp_id: int):
            super().__init__(lp_id)
            self.processed: int = 0

        async def coroutine_run(self) -> None:
            while True:
                ev = await self.wait_for("TASK")
                # Advance virtual time by processing duration
                await self.advance_time(2.0)
                self.processed += 1
                if self.processed >= 3:
                    break

    loop = BkSysCoEventLoop(end_time=100.0)
    worker = WorkerCoLP(lp_id=1)
    loop.register_lp(worker)

    # Schedule 3 tasks
    loop.schedule_event(create_event(timestamp=1.0, sender_id=0, receiver_id=1, event_type="TASK"))
    loop.schedule_event(create_event(timestamp=5.0, sender_id=0, receiver_id=1, event_type="TASK"))
    loop.schedule_event(create_event(timestamp=10.0, sender_id=0, receiver_id=1, event_type="TASK"))

    stats = loop.run()
    assert worker.processed == 3
    assert loop.current_time >= 12.0


def test_ladder_queue_high_volume_stress():
    """Verify LadderQueue stability and correctness under high event volumes (10,000 events)."""
    random.seed(12345)
    lq = LadderQueue(rung_width=2.5)
    n_events = 10000
    # Generate 10,000 random timestamps across [0.0, 1000.0]
    timestamps = [random.uniform(0.0, 1000.0) for _ in range(n_events)]

    for i, t in enumerate(timestamps):
        lq.push(create_event(timestamp=t, sender_id=1, receiver_id=2, event_type="STRESS", payload={"id": i}))

    assert len(lq) == n_events

    popped_times = []
    while not lq.is_empty():
        ev = lq.pop()
        popped_times.append(ev.timestamp)

    assert len(popped_times) == n_events
    # Must be strictly non-decreasing
    for i in range(len(popped_times) - 1):
        assert popped_times[i] <= popped_times[i + 1], f"Monotonicity failed at index {i}"


def test_logical_process_custom_handlers():
    """Verify custom event handler dispatching in BkSysLogicalProcess."""
    lp = BkSysLogicalProcess(lp_id="CustomWorker")
    received_types = []

    def handle_alert(ev: Event) -> None:
        received_types.append(("ALERT", ev.payload.get("level")))

    def handle_checkpoint(ev: Event) -> None:
        received_types.append(("CHECKPOINT", ev.payload.get("step")))

    lp.register_handler("ALERT", handle_alert)
    lp.register_handler("CHECKPOINT", handle_checkpoint)

    ev1 = create_event(timestamp=1.0, sender_id="Sys", receiver_id="CustomWorker", event_type="ALERT", payload={"level": "CRITICAL"})
    ev2 = create_event(timestamp=2.0, sender_id="Sys", receiver_id="CustomWorker", event_type="CHECKPOINT", payload={"step": 42})

    lp.handle_event(ev1)
    lp.handle_event(ev2)

    assert received_types == [("ALERT", "CRITICAL"), ("CHECKPOINT", 42)]


