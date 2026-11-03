import random
import math
import pytest
from bkitevsim.core.event import Event, EventType
from bkitevsim.core.priority_queue import MinHeapPriorityQueue, LadderQueue
from bkitevsim.core.dispatcher import Dispatcher
from bkitevsim.models.single_queue import SourceLP, QueueServerLP, SinkLP
from bkitevsim.models.network import QueuingNetwork
from bkitevsim.utils.theory import (
    mm1_theory,
    mm1k_theory,
    mminf_theory,
    mmc_theory,
    mmck_theory,
    erlang_b,
    erlang_c,
    network_pipeline_theory,
)
from bkitevsim.utils.metrics import compute_relative_error


def test_priority_queue_monotonicity():
    """Verification: Event queue must pop strictly in non-decreasing timestamp order."""
    pq = MinHeapPriorityQueue()
    timestamps = [10.5, 2.1, 4.8, 1.0, 7.3, 0.5, 9.9]
    for i, t in enumerate(timestamps):
        pq.push(Event(timestamp=t, event_id=i))

    popped = []
    while not pq.is_empty():
        popped.append(pq.pop().timestamp)

    assert popped == sorted(timestamps), "Priority queue did not preserve monotonic time ordering"


def test_ladder_queue_consistency():
    """Verification: LadderQueue produces exact same sorted order as min-heap."""
    lq = LadderQueue(rung_width=2.0)
    timestamps = [12.0, 3.5, 1.2, 8.4, 0.2, 5.0, 15.1, 2.8]
    for i, t in enumerate(timestamps):
        lq.push(Event(timestamp=t, event_id=i))

    popped = [lq.pop().timestamp for _ in range(len(timestamps))]
    assert popped == sorted(timestamps), "LadderQueue failed to preserve sorted order"


def test_event_conservation_law():
    """Verification: Conservation of jobs: Total Arrived = Completed + In_System + Dropped."""
    random.seed(42)
    dispatcher = Dispatcher()
    source = SourceLP(lp_id="Source", dest_lp_id="Server", arrival_rate=10.0)
    server = QueueServerLP(lp_id="Server", dest_lp_id="Sink", service_rate=8.0, capacity=15)
    sink = SinkLP(lp_id="Sink")

    dispatcher.register_lp(source)
    dispatcher.register_lp(server)
    dispatcher.register_lp(sink)

    source.start()
    sim_time = 500.0
    dispatcher.run(sim_time)

    metrics = server.metrics.finalize(sim_time)
    arrived = metrics["arrived"]
    completed = metrics["completed"]
    dropped = metrics["dropped"]
    in_system = server.total_in_system

    # Conservation must strictly hold: Arrived == Completed + Dropped + Currently_in_System
    assert arrived == completed + dropped + in_system, (
        f"Conservation violated: Arrived({arrived}) != Completed({completed}) + Dropped({dropped}) + InSystem({in_system})"
    )


def test_causality_trace_analysis():
    """Verification: Computational trace timestamps must be monotonic t_i <= t_{i+1}."""
    random.seed(42)
    dispatcher = Dispatcher()
    source = SourceLP(lp_id="Source", dest_lp_id="Server", arrival_rate=5.0)
    server = QueueServerLP(lp_id="Server", dest_lp_id="Sink", service_rate=6.0)
    sink = SinkLP(lp_id="Sink")

    dispatcher.register_lp(source)
    dispatcher.register_lp(server)
    dispatcher.register_lp(sink)

    source.start()
    dispatcher.run(100.0)

    trace = dispatcher.trace_log
    assert len(trace) > 10, "Trace log too short"
    for i in range(len(trace) - 1):
        assert trace[i]["timestamp"] <= trace[i+1]["timestamp"], (
            f"Causality violation at trace step {i}: {trace[i]['timestamp']} > {trace[i+1]['timestamp']}"
        )


def test_mm1_validation_accuracy():
    """Validation: Simulation results for M/M/1 must match theory within 5% error."""
    random.seed(42)
    lam, mu = 6.0, 10.0
    theory = mm1_theory(lam, mu)

    dispatcher = Dispatcher()
    source = SourceLP(lp_id="Source", dest_lp_id="Server", arrival_rate=lam)
    server = QueueServerLP(lp_id="Server", dest_lp_id="Sink", service_rate=mu)
    sink = SinkLP(lp_id="Sink")

    dispatcher.register_lp(source)
    dispatcher.register_lp(server)
    dispatcher.register_lp(sink)

    source.start()
    sim_time = 5000.0
    dispatcher.run(sim_time)

    metrics = server.metrics.finalize(sim_time)
    err_w = compute_relative_error(metrics["W"], theory["W"])
    err_l = compute_relative_error(metrics["L"], theory["L"])

    assert err_w < 5.0, f"M/M/1 Response time validation failed: error={err_w:.2f}%"
    assert err_l < 5.0, f"M/M/1 Queue length validation failed: error={err_l:.2f}%"


def test_erlang_b_loss_validation():
    """Validation: M/M/n/n Erlang loss drop rate must match Erlang-B formula within 5% error."""
    random.seed(42)
    lam, mu, n = 8.0, 2.0, 5  # a = 4.0 Erlangs, n = 5 servers
    theory_pb = erlang_b(n, lam / mu)

    dispatcher = Dispatcher()
    source = SourceLP(lp_id="Source", dest_lp_id="Server", arrival_rate=lam)
    server = QueueServerLP(lp_id="Server", dest_lp_id="Sink", service_rate=mu, num_servers=n, capacity=n)
    sink = SinkLP(lp_id="Sink")

    dispatcher.register_lp(source)
    dispatcher.register_lp(server)
    dispatcher.register_lp(sink)

    source.start()
    sim_time = 5000.0
    dispatcher.run(sim_time)

    metrics = server.metrics.finalize(sim_time, num_servers=n)
    err_pb = compute_relative_error(metrics["drop_rate"], theory_pb)

    assert err_pb < 5.0, f"Erlang-B validation failed: sim={metrics['drop_rate']:.4f}, theory={theory_pb:.4f}, err={err_pb:.2f}%"


def test_queuing_network_connectivity():
    """Validation: Network topology in Figure 1 completes end-to-end processing without deadlock."""
    random.seed(42)
    dispatcher = Dispatcher()
    net = QueuingNetwork(arrival_rate=2.0)
    net.register_all(dispatcher)
    net.start()

    res = dispatcher.run(500.0)
    net_stats = net.get_results(500.0)

    assert net_stats["completed_jobs"] > 500, "Network failed to process jobs"
    assert net_stats["avg_end_to_end_latency"] > 0.0, "Latency must be strictly positive"
    assert net_stats["bottleneck_node"] in ["io", "cpu", "printer", "disk"]


def test_queuing_network_jackson_validation():
    """Validation: Multi-hop network node latencies match Jackson theorem within 5%."""
    random.seed(42)
    dispatcher = Dispatcher()
    net = QueuingNetwork(arrival_rate=2.0)
    net.register_all(dispatcher)
    net.start()

    sim_time = 5000.0
    dispatcher.run(sim_time)
    results = net.get_results(sim_time)
    theory = network_pipeline_theory(2.0, mu_io=8.0, mu_cpu=10.0, mu_printer=4.0, mu_disk=6.0)

    # 1. End-to-end latency validation
    err_total_w = compute_relative_error(results["avg_end_to_end_latency"], theory["total_W"])
    assert err_total_w < 5.0, f"End-to-end latency error {err_total_w:.2f}% exceeds 5%"

    # 2. Node-level latency validation (Jackson theorem)
    for node_name in ["io", "cpu", "printer", "disk"]:
        sim_w = results["nodes"][node_name]["W"]
        th_w = theory["nodes"][node_name]["W"]
        err_w = compute_relative_error(sim_w, th_w)
        assert err_w < 5.0, f"Node {node_name} latency error {err_w:.2f}% exceeds 5%"


def test_mm1k_validation_accuracy():
    """Validation: Finite capacity M/M/1/K drop rate and metrics match theory within 5%."""
    random.seed(42)
    lam, mu, K = 8.0, 10.0, 5
    theory = mm1k_theory(lam, mu, K)

    dispatcher = Dispatcher()
    source = SourceLP(lp_id="Source", dest_lp_id="Server", arrival_rate=lam)
    server = QueueServerLP(lp_id="Server", dest_lp_id="Sink", service_rate=mu, num_servers=1, capacity=K)
    sink = SinkLP(lp_id="Sink")

    dispatcher.register_lp(source)
    dispatcher.register_lp(server)
    dispatcher.register_lp(sink)

    source.start()
    sim_time = 3000.0
    dispatcher.run(sim_time)

    metrics = server.metrics.finalize(sim_time, num_servers=1)
    err_pb = compute_relative_error(metrics["drop_rate"], theory["drop_rate"])
    err_w = compute_relative_error(metrics["W"], theory["W"])
    err_l = compute_relative_error(metrics["L"], theory["L"])

    assert err_pb < 5.0, f"M/M/1/K drop rate error {err_pb:.2f}% exceeds 5%"
    assert err_w < 5.0, f"M/M/1/K latency error {err_w:.2f}% exceeds 5%"
    assert err_l < 5.0, f"M/M/1/K customer count error {err_l:.2f}% exceeds 5%"


def test_mmc_validation_accuracy():
    """Validation: Multi-server M/M/c metrics match Erlang-C theory within 5%."""
    random.seed(42)
    lam, mu, c = 15.0, 6.0, 3
    theory = mmc_theory(lam, mu, c)

    dispatcher = Dispatcher()
    source = SourceLP(lp_id="Source", dest_lp_id="Server", arrival_rate=lam)
    server = QueueServerLP(lp_id="Server", dest_lp_id="Sink", service_rate=mu, num_servers=c)
    sink = SinkLP(lp_id="Sink")

    dispatcher.register_lp(source)
    dispatcher.register_lp(server)
    dispatcher.register_lp(sink)

    source.start()
    sim_time = 3000.0
    dispatcher.run(sim_time)

    metrics = server.metrics.finalize(sim_time, num_servers=c)
    err_w = compute_relative_error(metrics["W"], theory["W"])
    err_l = compute_relative_error(metrics["L"], theory["L"])

    assert err_w < 5.0, f"M/M/c latency error {err_w:.2f}% exceeds 5%"
    assert err_l < 5.0, f"M/M/c customer count error {err_l:.2f}% exceeds 5%"


def test_mminf_validation_accuracy():
    """Validation: Pure delay M/M/infinity model matches theory within 5%."""
    random.seed(42)
    lam, mu = 10.0, 2.0
    theory = mminf_theory(lam, mu)

    dispatcher = Dispatcher()
    source = SourceLP(lp_id="Source", dest_lp_id="Server", arrival_rate=lam)
    # 100 servers acts as infinite servers for lambda/mu = 5
    server = QueueServerLP(lp_id="Server", dest_lp_id="Sink", service_rate=mu, num_servers=100)
    sink = SinkLP(lp_id="Sink")

    dispatcher.register_lp(source)
    dispatcher.register_lp(server)
    dispatcher.register_lp(sink)

    source.start()
    sim_time = 2000.0
    dispatcher.run(sim_time)

    metrics = server.metrics.finalize(sim_time, num_servers=100)
    err_w = compute_relative_error(metrics["W"], theory["W"])
    err_l = compute_relative_error(metrics["L"], theory["L"])

    assert err_w < 5.0, f"M/M/inf latency error {err_w:.2f}% exceeds 5%"
    assert err_l < 5.0, f"M/M/inf count error {err_l:.2f}% exceeds 5%"
    assert metrics["Wq"] == 0.0 or metrics["Wq"] < 0.01, "M/M/inf must have near zero waiting time"


def test_mmck_validation_accuracy():
    """Validation: Multi-server finite buffer M/M/c/K matches theory within 5%."""
    random.seed(42)
    lam, mu, c, K = 14.0, 5.0, 2, 5
    theory = mmck_theory(lam, mu, c, K)

    dispatcher = Dispatcher()
    source = SourceLP(lp_id="Source", dest_lp_id="Server", arrival_rate=lam)
    server = QueueServerLP(lp_id="Server", dest_lp_id="Sink", service_rate=mu, num_servers=c, capacity=K)
    sink = SinkLP(lp_id="Sink")

    dispatcher.register_lp(source)
    dispatcher.register_lp(server)
    dispatcher.register_lp(sink)

    source.start()
    sim_time = 3000.0
    dispatcher.run(sim_time)

    metrics = server.metrics.finalize(sim_time, num_servers=c)
    err_pb = compute_relative_error(metrics["drop_rate"], theory["drop_rate"])
    err_w = compute_relative_error(metrics["W"], theory["W"])

    assert err_pb < 5.0, f"M/M/c/K drop rate error {err_pb:.2f}% exceeds 5%"
    assert err_w < 5.0, f"M/M/c/K latency error {err_w:.2f}% exceeds 5%"


def test_littles_law_invariant():
    """Verification: Little's Law invariant L = lambda_eff * W holds on arbitrary model."""
    random.seed(42)
    disp = Dispatcher()
    src = SourceLP("Source", "Server", arrival_rate=12.0)
    srv = QueueServerLP("Server", "Sink", service_rate=5.0, num_servers=2, capacity=8)
    snk = SinkLP("Sink")

    disp.register_lp(src)
    disp.register_lp(srv)
    disp.register_lp(snk)

    src.start()
    disp.run(2000.0)

    m = srv.metrics.finalize(2000.0, num_servers=2)
    lam_eff = 12.0 * (1.0 - m["drop_rate"])
    littles_L = lam_eff * m["W"]
    littles_Lq = lam_eff * m["Wq"]

    err_l = compute_relative_error(m["L"], littles_L)
    err_lq = compute_relative_error(m["Lq"], littles_Lq)

    assert err_l < 2.0, f"Little's Law L = lambda_eff * W violated: err={err_l:.2f}%"
    assert err_lq < 2.0, f"Little's Law Lq = lambda_eff * Wq violated: err={err_lq:.2f}%"


def test_seed_reproducibility():
    """Verification: Common Random Numbers (CRN) bit-exact deterministic reproducibility."""
    def run_sim(seed: int) -> float:
        random.seed(seed)
        d = Dispatcher()
        s1 = SourceLP("Source", "Server", arrival_rate=6.0)
        s2 = QueueServerLP("Server", "Sink", service_rate=8.0)
        s3 = SinkLP("Sink")
        d.register_lp(s1)
        d.register_lp(s2)
        d.register_lp(s3)
        s1.start()
        d.run(500.0)
        return s2.metrics.finalize(500.0)["W"]

    w1 = run_sim(12345)
    w2 = run_sim(12345)
    assert w1 == w2, f"Simulations with same seed produced different results: {w1} != {w2}"


def test_exponential_workload_generator():
    """Verification: Inverse Transform Sampling generates true Exponential interarrival times."""
    random.seed(42)
    lam = 8.0
    n_samples = 50000
    # Inverse transform sampling: X = -ln(1 - U) / lambda
    samples = [-math.log(1.0 - random.random()) / lam for _ in range(n_samples)]

    sample_mean = sum(samples) / n_samples
    sample_var = sum((x - sample_mean) ** 2 for x in samples) / (n_samples - 1)

    theory_mean = 1.0 / lam
    theory_var = 1.0 / (lam ** 2)

    err_mean = compute_relative_error(sample_mean, theory_mean)
    err_var = compute_relative_error(sample_var, theory_var)

    assert err_mean < 2.0, f"Exponential mean error {err_mean:.2f}% exceeds 2%"
    assert err_var < 3.0, f"Exponential variance error {err_var:.2f}% exceeds 3%"

