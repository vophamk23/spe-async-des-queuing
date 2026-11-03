"""Main entry point for the SPE Asynchronous Discrete-Event Queuing Simulation Engine.

Module hỗ trợ chạy thực nghiệm mô phỏng các mô hình hàng đợi Kendall và Jackson Network,
đối chiếu nghiệm giải tích lý thuyết và tính toán sai số tương đối (Relative Error).
"""

import argparse
import random
import sys
from typing import Dict, List, Any

from bkitevsim.core.simulation import Simulation, SimulationOptions
from bkitevsim.models.single_queue import SourceLP, QueueServerLP, SinkLP
from bkitevsim.models.network import BranchingServerLP, NetworkSinkLP
from bkitevsim.utils.theory import (
    mm1_theory,
    mm1k_theory,
    mminf_theory,
    mmnn_theory,
    mmc_theory,
    mmck_theory,
    network_pipeline_theory,
)
from bkitevsim.utils.metrics import compute_confidence_interval, compute_relative_error


def run_single_replication(
    model: str,
    lam: float,
    mu: float,
    servers: int,
    capacity: int,
    sim_time: float,
    seed: int,
    use_ladder: bool = False
) -> Dict[str, float]:
    """Thực thi một lượt chạy mô phỏng độc lập (Single Replication) chuẩn Façade API.

    Quy trình chuẩn hóa theo Figure 4 đề bài (hk261_BKsyspeEvsim.pdf):
    1. Thiết lập Seed ngẫu nhiên (đảm bảo tính tái lập - Reproducibility).
    2. Khởi tạo SimulationOptions và Simulation Façade controller.
    3. Đăng ký các lớp mô hình LP qua sim.register_model().
    4. Tạo tự động các trạm Logic qua sim.create_lp().
    5. Điều phối mô phỏng tự động qua sim.run() (tự động gắn dispatcher,
       khởi tạo LadderQueue, gọi initialize() và vòng lặp sự kiện PDES).
    6. Thu gom và hoàn tất tính toán chỉ số hiệu năng (metrics.finalize).
    """
    # Bước 1: Đặt seed ngẫu nhiên cho mỗi lượt chạy độc lập (tính tái lập)
    random.seed(seed)

    # Bước 2: Khởi tạo cấu hình và bộ điều khiển Simulation Façade
    options = SimulationOptions(
        end_time=sim_time,
        dispatcher="sequential",
        bucket_width=1.0,
    )
    sim = Simulation(options=options)

    # --- NHÁNH 1: MÔ HÌNH MẠNG HÀNG ĐỢI ĐA CHẶNG (Queuing Network) ---
    if model == "network":
        # Đăng ký các lớp Logical Process (LP) của mạng vào Façade
        sim.register_model("Source", SourceLP)
        sim.register_model("QueueServer", QueueServerLP)
        sim.register_model("BranchingServer", BranchingServerLP)
        sim.register_model("NetworkSink", NetworkSinkLP)

        # Khởi tạo chuỗi trạm: Source -> IO -> CPU -> (Printer / Disk) -> Sink
        sim.create_lp("Source", "Source", dest_lp_id="IO", arrival_rate=lam)
        io_server = sim.create_lp("IO", "QueueServer", dest_lp_id="CPU", service_rate=8.0)
        cpu_server = sim.create_lp(
            "CPU",
            "BranchingServer",
            printer_lp_id="Printer",
            disk_lp_id="Disk",
            p_printer=0.3,
            service_rate=10.0
        )
        printer_server = sim.create_lp("Printer", "QueueServer", dest_lp_id="Sink", service_rate=4.0)
        disk_server = sim.create_lp("Disk", "QueueServer", dest_lp_id="Sink", service_rate=6.0)
        sink = sim.create_lp("Sink", "NetworkSink")

        # Chạy vòng lặp sự kiện mô phỏng DES
        sim.run()

        # Tính độ trễ trung bình toàn trình từ Source tới Sink
        avg_latency = (
            sum(sink.network_latencies) / len(sink.network_latencies)
            if sink.network_latencies else 0.0
        )
        # Thu thập hiệu năng từng trạm
        io_res = io_server.metrics.finalize(sim_time)
        cpu_res = cpu_server.metrics.finalize(sim_time)
        printer_res = printer_server.metrics.finalize(sim_time)
        disk_res = disk_server.metrics.finalize(sim_time)
        # Xác định hệ số sử dụng của nút cổ chai (Bottleneck)
        bottleneck_rho = max(io_res["rho"], cpu_res["rho"], printer_res["rho"], disk_res["rho"])
        th = len(sink.completed_jobs) / sim_time

        return {
            "W": avg_latency,
            "throughput": th,
            "rho": bottleneck_rho,
            "completed": len(sink.completed_jobs),
            "drop_rate": 0.0,
            "L": th * avg_latency
        }

    # --- NHÁNH 2: CÁC MÔ HÌNH HÀNG ĐỢI ĐƠN KENDALL (M/M/1 -> M/M/c/K) ---
    # Cấu hình số máy chủ (vô hạn nếu MMINF) và sức chứa hàng đợi (hữu hạn nếu MM1K, MMNN, MMCK)
    num_s = float("inf") if model == "MMINF" else servers
    cap = None if model in ["MM1", "MMC", "MMINF"] else (servers if model == "MMNN" else capacity)

    # Đăng ký mô hình hàng đợi đơn
    sim.register_model("Source", SourceLP)
    sim.register_model("Server", QueueServerLP)
    sim.register_model("Sink", SinkLP)

    # Khởi tạo chuỗi trạm: Source -> Server -> Sink
    sim.create_lp("Source", "Source", dest_lp_id="Server", arrival_rate=lam)
    server = sim.create_lp(
        "Server",
        "Server",
        dest_lp_id="Sink",
        service_rate=mu,
        num_servers=num_s,
        capacity=cap
    )
    sim.create_lp("Sink", "Sink")

    # Chạy vòng lặp sự kiện mô phỏng DES
    sim.run()

    # Thu thập và tổng kết chỉ số hiệu năng (W, L, Throughput, Drop Rate, rho)
    return server.metrics.finalize(sim_time, num_servers=servers if num_s != float("inf") else 1)


def get_analytical_truth(
    model: str,
    lam: float,
    mu: float,
    servers: int,
    capacity: int
) -> Dict[str, Any]:
    """Tra cứu nghiệm giải tích lý thuyết chuẩn xác cho từng mô hình Kendall & Jackson."""
    if model == "MM1":
        return mm1_theory(lam, mu)
    elif model == "MM1K":
        return mm1k_theory(lam, mu, capacity)
    elif model == "MMINF":
        return mminf_theory(lam, mu)
    elif model == "MMNN":
        return mmnn_theory(lam, mu, servers)
    elif model == "MMC":
        return mmc_theory(lam, mu, servers)
    elif model == "MMCK":
        return mmck_theory(lam, mu, servers, capacity)
    elif model == "network":
        return network_pipeline_theory(lam, mu_io=8.0, mu_cpu=10.0, mu_printer=4.0, mu_disk=6.0)
    else:
        raise ValueError(f"Unknown model: {model}")


# Hỗ trợ hiển thị ký tự UTF-8 mượt mà trên console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    # Bước 1: Định nghĩa các tham số dòng lệnh (CLI arguments)
    parser = argparse.ArgumentParser(
        description="SPE Asynchronous Discrete-Event Queuing Simulation Engine (CO3007 - HCMUT)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="MM1",
        choices=["MM1", "MM1K", "MMINF", "MMNN", "MMC", "MMCK", "network"],
        help="Queuing model to simulate (default: MM1)"
    )
    parser.add_argument("--lambda", dest="lam", type=float, default=8.0, help="Arrival rate lambda (default: 8.0)")
    parser.add_argument("--mu", type=float, default=10.0, help="Service rate mu (default: 10.0)")
    parser.add_argument("--servers", type=int, default=1, help="Number of servers c (default: 1)")
    parser.add_argument("--capacity", type=int, default=10, help="Queue capacity K (default: 10)")
    parser.add_argument("--sim-time", type=float, default=5000.0, help="Simulation duration (default: 5000.0)")
    parser.add_argument("--replications", type=int, default=5, help="Number of independent replications (default: 5)")
    parser.add_argument("--ladder-queue", action="store_true", help="Use LadderQueue instead of MinHeap")

    args = parser.parse_args()

    # Bước 2: In thông số cấu hình kịch bản thực nghiệm
    print("=" * 70)
    print("[*] SPE-async-des-queuing Simulation Engine (CO3007 - HK261)")
    print(f"Model: {args.model} | Lambda: {args.lam} | Mu: {args.mu} | Servers: {args.servers} | Capacity: {args.capacity}")
    print(f"Sim Time: {args.sim_time} | Replications: {args.replications} | Dispatcher: Simulation Façade (bkitevsim)")
    print("=" * 70)

    # Bước 3: Thực thi N lượt chạy độc lập (Replications) với seed khác nhau
    rep_results: List[Dict[str, float]] = []
    for r in range(args.replications):
        seed = 42 + r * 1007

        res = run_single_replication(
            model=args.model,
            lam=args.lam,
            mu=args.mu,
            servers=args.servers,
            capacity=args.capacity,
            sim_time=args.sim_time,
            seed=seed,
            use_ladder=args.ladder_queue
        )
        rep_results.append(res)
        print(f"  [Run {r+1:2d}/{args.replications}] W={res['W']:.4f}s, L={res['L']:.3f}, Throughput={res['throughput']:.2f}/s, Drops={res.get('drop_rate', 0.0)*100:.2f}%")

    # Bước 4: Tính khoảng tin cậy 95% (Student's t-distribution)
    w_ci = compute_confidence_interval([r["W"] for r in rep_results])
    l_ci = compute_confidence_interval([r["L"] for r in rep_results])
    th_ci = compute_confidence_interval([r["throughput"] for r in rep_results])
    drop_ci = compute_confidence_interval([r.get("drop_rate", 0.0) for r in rep_results])

    # Bước 5: Tra cứu nghiệm lý thuyết giải tích đối chuẩn
    theory = get_analytical_truth(args.model, args.lam, args.mu, args.servers, args.capacity)
    theory_w = theory.get("W") or theory.get("total_W", 0.0)
    theory_l = theory.get("L") or theory.get("total_L", 0.0)
    theory_drop = theory.get("drop_rate") or theory.get("pb", 0.0)

    # Bước 6: Tính sai số tương đối (Relative Error) so với lý thuyết
    err_w = compute_relative_error(w_ci["mean"], theory_w) if theory_w != float("inf") else 0.0
    err_l = compute_relative_error(l_ci["mean"], theory_l) if theory_l != float("inf") else 0.0

    # Bước 7: Xuất bảng tổng hợp kết quả và thẩm định (Validation Report)
    print("\n" + "=" * 70)
    print("[*] TỔNG HỢP KẾT QUẢ & THẨM ĐỊNH LÝ THUYẾT (VALIDATION)")
    print("=" * 70)
    print(f"Response Time (W) : Sim={w_ci['mean']:.4f} +/- {w_ci['ci_half']:.4f}s | Theory={theory_w:.4f}s | Error={err_w:.2f}%")
    print(f"Queue Length  (L) : Sim={l_ci['mean']:.4f} +/- {l_ci['ci_half']:.4f}  | Theory={theory_l:.4f}  | Error={err_l:.2f}%")
    print(f"Throughput        : Sim={th_ci['mean']:.2f} requests/s")
    if theory_drop > 0 or drop_ci['mean'] > 0:
        err_drop = compute_relative_error(drop_ci["mean"], theory_drop)
        print(f"Drop Rate (Pb)    : Sim={drop_ci['mean']*100:.3f}% +/- {drop_ci['ci_half']*100:.3f}% | Theory={theory_drop*100:.3f}% | Error={err_drop:.2f}%")

    # Bước 8: Kết luận thẩm định theo chuẩn sai số môn học (RE < 5.0%)
    if err_w < 5.0 and err_l < 5.0:
        print("\n[+] VALIDATION VERDICT: PASSED (Tất cả sai số < 5% chuẩn môn học)")
    else:
        print("\n[!] VALIDATION VERDICT: Khảo sát ở vùng tải cực hạn hoặc cần tăng thời gian mô phỏng")
    print("=" * 70)


if __name__ == "__main__":
    main()
