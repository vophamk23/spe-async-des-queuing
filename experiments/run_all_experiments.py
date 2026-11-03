import os
import sys
import time
from typing import List, Dict, Any

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from main import run_single_replication
from bkitevsim.utils.theory import (
    mm1_theory,
    mm1k_theory,
    erlang_b,
    mmc_theory,
    network_pipeline_theory,
)
from bkitevsim.utils.metrics import compute_confidence_interval, compute_relative_error
from bkitevsim.utils.visualizer import (
    plot_simulation_vs_theory,
    plot_sensitivity_buffer,
    plot_network_bottleneck,
    ensure_plot_dir
)


def run_mm1_sweep(sim_time: float = 3000.0, replications: int = 5) -> None:
    print("\n" + "=" * 75)
    print("🔬 EXPERIMENT 1: M/M/1 KHẢO SÁT TỪ TẢI NHẸ ĐẾN TẢI CỰC NẶNG (rho in [0.1, 0.95])")
    print("=" * 75)
    mu = 10.0
    rho_targets = [0.1, 0.2, 0.4, 0.6, 0.8, 0.85, 0.9, 0.95]
    
    sim_w_means, sim_w_ci, theory_w_list = [], [], []
    sim_l_means, sim_l_ci, theory_l_list = [], [], []

    for rho in rho_targets:
        lam = rho * mu
        theory = mm1_theory(lam, mu)
        
        rep_w, rep_l = [], []
        for r in range(replications):
            seed = 100 + r * 37
            res = run_single_replication(
                model="MM1", lam=lam, mu=mu, servers=1, capacity=10,
                sim_time=sim_time, seed=seed
            )
            rep_w.append(res["W"])
            rep_l.append(res["L"])

        w_stat = compute_confidence_interval(rep_w)
        l_stat = compute_confidence_interval(rep_l)

        sim_w_means.append(w_stat["mean"])
        sim_w_ci.append(w_stat["ci_half"])
        theory_w_list.append(theory["W"])

        sim_l_means.append(l_stat["mean"])
        sim_l_ci.append(l_stat["ci_half"])
        theory_l_list.append(theory["L"])

        err_w = compute_relative_error(w_stat["mean"], theory["W"])
        print(f"  rho={rho:0.2f} (lam={lam:4.1f}) | W_sim={w_stat['mean']:.4f}s, W_th={theory['W']:.4f}s | Err={err_w:.2f}% | L={l_stat['mean']:.2f}")

    # Plot response time comparison
    plot_simulation_vs_theory(
        x_vals=rho_targets,
        sim_means=sim_w_means,
        sim_ci_halfs=sim_w_ci,
        theory_vals=theory_w_list,
        x_label="He so tai (rho = lambda / mu)",
        y_label="Thoi gian dap ung trung binh W (giay)",
        title="Tham dinh Mo hinh M/M/1: Ly thuyet vs Mo phong (95% CI)",
        filename="mm1_response_time_validation.png"
    )
    print("  -> Da luu bieu do: plots/mm1_response_time_validation.png")


def run_mm1k_buffer_sensitivity(sim_time: float = 3000.0, replications: int = 5) -> None:
    print("\n" + "=" * 75)
    print("🔬 EXPERIMENT 2: M/M/1/K PHÂN TÍCH ĐỘ NHẠY BỘ ĐỆM (K in [3, 5, 10, 20, 30, 50])")
    print("=" * 75)
    lam, mu = 9.0, 10.0  # High load rho = 0.9
    k_values = [3, 5, 8, 12, 20, 30, 50]
    
    avg_drops, avg_waits = [], []

    for k in k_values:
        rep_drop, rep_wq = [], []
        for r in range(replications):
            seed = 200 + r * 41
            res = run_single_replication(
                model="MM1K", lam=lam, mu=mu, servers=1, capacity=k,
                sim_time=sim_time, seed=seed
            )
            rep_drop.append(res.get("drop_rate", 0.0))
            rep_wq.append(res.get("Wq", 0.0))

        d_stat = compute_confidence_interval(rep_drop)
        w_stat = compute_confidence_interval(rep_wq)
        avg_drops.append(d_stat["mean"])
        avg_waits.append(w_stat["mean"])

        theory = mm1k_theory(lam, mu, k)
        print(f"  K={k:2d} | Drop_sim={d_stat['mean']*100:6.3f}%, Drop_th={theory['pb']*100:6.3f}% | Wq={w_stat['mean']:.4f}s")

    plot_sensitivity_buffer(
        k_vals=k_values,
        drop_rates=avg_drops,
        wait_times=avg_waits,
        title="Phan tich Do nhay Bo dem K: Danh doi Ti le Drop vs Do tre cho Wq",
        filename="mm1k_buffer_tradeoff.png"
    )
    print("  -> Da luu bieu do: plots/mm1k_buffer_tradeoff.png")


def run_erlang_loss_sweep(sim_time: float = 3000.0, replications: int = 5) -> None:
    print("\n" + "=" * 75)
    print("🔬 EXPERIMENT 3: M/M/n/n HE THONG ERLANG LOSS & CONG THUC ERLANG-B")
    print("=" * 75)
    n = 5  # 5 servers, 0 buffer
    mu = 2.0
    a_values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]  # Erlang load = lambda / mu
    
    sim_drops, sim_ci, theory_pb_list = [], [], []

    for a in a_values:
        lam = a * mu
        theory_pb = erlang_b(n, a)
        
        rep_drop = []
        for r in range(replications):
            seed = 300 + r * 53
            res = run_single_replication(
                model="MMNN", lam=lam, mu=mu, servers=n, capacity=n,
                sim_time=sim_time, seed=seed
            )
            rep_drop.append(res.get("drop_rate", 0.0))

        d_stat = compute_confidence_interval(rep_drop)
        sim_drops.append(d_stat["mean"])
        sim_ci.append(d_stat["ci_half"])
        theory_pb_list.append(theory_pb)

        err_pb = compute_relative_error(d_stat["mean"], theory_pb)
        print(f"  Load a={a:4.1f} (lam={lam:4.1f}) | Pb_sim={d_stat['mean']*100:6.3f}%, Pb_th={theory_pb*100:6.3f}% | Err={err_pb:.2f}%")

    plot_simulation_vs_theory(
        x_vals=a_values,
        sim_means=sim_drops,
        sim_ci_halfs=sim_ci,
        theory_vals=theory_pb_list,
        x_label="Tai Erlang (a = lambda / mu)",
        y_label="Xac suat mat goi (Pb)",
        title="Tham dinh He thong Erlang Loss (M/M/n/n) vs Cong thuc Erlang-B",
        filename="erlang_b_validation.png"
    )
    print("  -> Da luu bieu do: plots/erlang_b_validation.png")


def run_network_bottleneck_experiment(sim_time: float = 3000.0) -> None:
    print("\n" + "=" * 75)
    print("🔬 EXPERIMENT 4: MẠNG HÀNG ĐỢI ĐA CHẶNG & NHẬN DIỆN NÚT THẮT CỔ CHAI (BOTTLENECK)")
    print("=" * 75)
    # Figure 1: Source -> I/O (mu=8) -> CPU (mu=10) -> { Printer (mu=4, p=0.3), Disk (mu=6, p=0.7) } -> Sink
    lam = 3.5
    res = run_single_replication(
        model="network", lam=lam, mu=10.0, servers=1, capacity=10,
        sim_time=sim_time, seed=777
    )
    
    # Calculate detailed theory
    theory = network_pipeline_theory(lam, mu_io=8.0, mu_cpu=10.0, mu_printer=4.0, mu_disk=6.0, p_printer=0.3, p_disk=0.7)
    
    node_names = ["I/O Device", "CPU", "Printer", "Disk"]
    nodes_data = theory["nodes"]
    utilizations = [
        nodes_data["io"]["rho"],
        nodes_data["cpu"]["rho"],
        nodes_data["printer"]["rho"],
        nodes_data["disk"]["rho"]
    ]

    print(f"  Luu luong vao mang: lambda = {lam} req/s")
    for name, u in zip(node_names, utilizations):
        print(f"    - Nut {name:12s}: He so tai rho = {u*100:.1f}%")
    print(f"  ==> NUT THAT CO CHAI CHINH: {theory['bottleneck_node'].upper()} (rho = {theory['bottleneck_rho']*100:.1f}%)")
    print(f"  Thoi gian tre toan mang (End-to-End Latency W): {res['W']:.4f}s (Ly thuyet: {theory['total_W']:.4f}s)")

    plot_network_bottleneck(
        node_names=node_names,
        utilizations=utilizations,
        title=f"Queuing Network (Figure 1): He so ban rho (lambda={lam} req/s)",
        filename="network_bottleneck_analysis.png"
    )
    print("  -> Da luu bieu do: plots/network_bottleneck_analysis.png")


def main() -> None:
    print("*" * 75)
    print("🚀 BỘ CHẠY TOÀN DIỆN THỰC NGHIỆM ĐÁNH GIÁ HIỆU NĂNG HỆ THỐNG (CO3007)")
    print("*" * 75)
    ensure_plot_dir("plots")
    t0 = time.time()

    # 1. M/M/1 Sweep from light to heavy load
    run_mm1_sweep(sim_time=4000.0, replications=5)

    # 2. M/M/1/K Buffer Capacity Sensitivity Trade-off
    run_mm1k_buffer_sensitivity(sim_time=3000.0, replications=5)

    # 3. M/M/n/n Erlang Loss Validation
    run_erlang_loss_sweep(sim_time=4000.0, replications=5)

    # 4. Multi-Queue Network Bottleneck Analysis
    run_network_bottleneck_experiment(sim_time=4000.0)

    elapsed = time.time() - t0
    print("\n" + "*" * 75)
    print(f"[+] HOÀN TẤT TOÀN BỘ CÁC THỰC NGHIỆM TRONG {elapsed:.1f} GIÂY!")
    print("[+] Toàn bộ biểu đồ độ phân giải cao (300 DPI) đã xuất tại thư mục: plots/")
    print("*" * 75)


if __name__ == "__main__":
    main()
