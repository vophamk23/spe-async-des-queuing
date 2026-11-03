import math
from typing import Dict, Any


def mm1_theory(lam: float, mu: float) -> Dict[str, float]:
    """CÔNG THỨC GIẢI TÍCH MÔ HÌNH M/M/1 (Đơn server, hàng đợi vô hạn).
    
    Điều kiện ổn định: rho = lambda / mu < 1 (nếu rho >= 1, hàng đợi dài vô tận).
    Công thức cốt lõi:
    - W = 1 / (mu - lam)          : Thời gian lưu lại hệ thống trung bình.
    - Wq = rho / (mu - lam)        : Thời gian ngồi đợi trong hàng chờ.
    - L = lam * W = rho / (1 - rho): Số gói trung bình trong hệ thống (Định luật Little).
    - Lq = lam * Wq = rho^2 / (1 - rho)
    """
    if lam >= mu:
        return {
            "stable": False,
            "rho": lam / mu,
            "L": float("inf"),
            "Lq": float("inf"),
            "W": float("inf"),
            "Wq": float("inf"),
            "throughput": mu,
            "drop_rate": 0.0
        }
    rho = lam / mu
    L = rho / (1.0 - rho)
    Lq = (rho ** 2) / (1.0 - rho)
    W = 1.0 / (mu - lam)
    Wq = rho / (mu - lam)
    return {
        "stable": True,
        "rho": rho,
        "L": L,
        "Lq": Lq,
        "W": W,
        "Wq": Wq,
        "throughput": lam,
        "drop_rate": 0.0
    }


def mm1k_theory(lam: float, mu: float, K: int) -> Dict[str, float]:
    """CÔNG THỨC GIẢI TÍCH MÔ HÌNH M/M/1/K (Đơn server, sức chứa hữu hạn K).
    
    Hệ thống luôn ổn định ngay cả khi lambda >= mu vì các gói dư thừa sẽ bị Drop.
    - Xác suất trạng thái rỗng p0 = (1 - rho) / (1 - rho^(K+1)).
    - Xác suất rớt gói (Blocking probability) Pb = pK = p0 * rho^K.
    - Tốc độ đến hiệu dụng: lambda_eff = lambda * (1 - Pb).
    - Thời gian trễ theo Định luật Little: W = L / lambda_eff.
    """
    rho = lam / mu
    if abs(rho - 1.0) < 1e-9:
        p0 = 1.0 / (K + 1)
        pk = [p0] * (K + 1)
        L = K / 2.0
    else:
        p0 = (1.0 - rho) / (1.0 - (rho ** (K + 1)))
        pk = [p0 * (rho ** k) for k in range(K + 1)]
        L = (rho / (1.0 - rho)) - ((K + 1) * (rho ** (K + 1))) / (1.0 - (rho ** (K + 1)))

    pb = pk[K]  # Xác suất rớt gói (Blocking probability)
    lam_eff = lam * (1.0 - pb)
    W = L / lam_eff if lam_eff > 0 else 0.0
    Wq = max(0.0, W - (1.0 / mu))
    Lq = lam_eff * Wq
    return {
        "stable": True,
        "rho": rho,
        "pb": pb,
        "drop_rate": pb,
        "L": L,
        "Lq": Lq,
        "W": W,
        "Wq": Wq,
        "throughput": lam_eff
    }


def mminf_theory(lam: float, mu: float) -> Dict[str, float]:
    """CÔNG THỨC GIẢI TÍCH MÔ HÌNH M/M/infinity (Vô hạn server, trễ thuần túy).
    
    Không bao giờ có hàng chờ (Wq = 0, Lq = 0).
    - Thời gian trong hệ thống W = 1 / mu.
    - Số khách trung bình trong hệ thống L = lambda / mu (theo Định luật Little).
    """
    a = lam / mu
    return {
        "stable": True,
        "rho": a,
        "L": a,
        "Lq": 0.0,
        "W": 1.0 / mu,
        "Wq": 0.0,
        "throughput": lam,
        "drop_rate": 0.0
    }


def erlang_b(n: int, a: float) -> float:
    """CÔNG THỨC MẤT MÁT ERLANG-B (Tính bằng công thức đệ quy ổn định số học):
    
    B(k, a) = (a * B(k-1, a)) / (k + a * B(k-1, a)) với B(0, a) = 1.
    Tránh tràn số (Overflow) khi tính giai thừa n! với n lớn.
    """
    b = 1.0
    for k in range(1, n + 1):
        b = (a * b) / (k + a * b)
    return b


def mmnn_theory(lam: float, mu: float, n: int) -> Dict[str, float]:
    """CÔNG THỨC GIẢI TÍCH MÔ HÌNH M/M/n/n (Hệ thống từ chối Erlang Loss).
    
    Hệ thống có n server và không có ghế chờ.
    - Xác suất rớt cuộc gọi Pb = Erlang_B(n, a) với a = lambda / mu.
    - Thông lượng hiệu dụng: lambda_eff = lambda * (1 - Pb).
    - Số khách trung bình L = lambda_eff / mu.
    """
    a = lam / mu
    pb = erlang_b(n, a)
    lam_eff = lam * (1.0 - pb)
    L = lam_eff / mu
    return {
        "stable": True,
        "a": a,
        "pb": pb,
        "drop_rate": pb,
        "L": L,
        "Lq": 0.0,
        "W": 1.0 / mu,
        "Wq": 0.0,
        "throughput": lam_eff
    }


def erlang_c(c: int, a: float) -> float:
    """CÔNG THỨC ERLANG-C: Xác suất một khách đến phải chờ đợi trong hàng đợi M/M/c."""
    rho = a / c
    if rho >= 1.0:
        return 1.0
    sum_terms = sum((a ** k) / math.factorial(k) for k in range(c))
    c_term = ((a ** c) / math.factorial(c)) * (1.0 / (1.0 - rho))
    p0 = 1.0 / (sum_terms + c_term)
    return c_term * p0


def mmc_theory(lam: float, mu: float, c: int) -> Dict[str, float]:
    """CÔNG THỨC GIẢI TÍCH MÔ HÌNH M/M/c (Đa máy chủ song song, hàng đợi vô hạn).
    
    Điều kiện ổn định: rho = lambda / (c * mu) < 1.
    - prob_queue = Erlang_C(c, a): Xác suất phải xếp hàng chờ.
    - Lq = prob_queue * (rho / (1 - rho)).
    - Wq = Lq / lambda.
    - W = Wq + 1 / mu.
    - L = Lq + lambda / mu.
    """
    a = lam / mu
    rho = a / c
    if rho >= 1.0:
        return {
            "stable": False,
            "rho": rho,
            "L": float("inf"),
            "Lq": float("inf"),
            "W": float("inf"),
            "Wq": float("inf"),
            "throughput": c * mu,
            "drop_rate": 0.0
        }

    sum_terms = sum((a ** k) / math.factorial(k) for k in range(c))
    c_term = ((a ** c) / math.factorial(c)) * (1.0 / (1.0 - rho))
    p0 = 1.0 / (sum_terms + c_term)

    prob_queue = c_term * p0
    Lq = prob_queue * (rho / (1.0 - rho))
    Wq = Lq / lam
    W = Wq + (1.0 / mu)
    L = Lq + a
    return {
        "stable": True,
        "rho": rho,
        "prob_queue": prob_queue,
        "L": L,
        "Lq": Lq,
        "W": W,
        "Wq": Wq,
        "throughput": lam,
        "drop_rate": 0.0
    }


def mmck_theory(lam: float, mu: float, c: int, K: int) -> Dict[str, float]:
    """CÔNG THỨC GIẢI TÍCH MÔ HÌNH M/M/c/K (Đa máy chủ, sức chứa hữu hạn K).
    
    Giải hệ phân phối xác suất trạng thái dừng pk (k = 0..K):
    - k <= c: pk tỉ lệ với a^k / k!
    - c < k <= K: pk tỉ lệ với (a^c / c!) * rho^(k-c)
    """
    a = lam / mu
    rho = a / c

    p_unnorm = [1.0] * (K + 1)
    for k in range(1, K + 1):
        if k <= c:
            p_unnorm[k] = (a ** k) / math.factorial(k)
        else:
            p_unnorm[k] = p_unnorm[c] * (rho ** (k - c))

    p0 = 1.0 / sum(p_unnorm)
    pk = [u * p0 for u in p_unnorm]

    pb = pk[K]
    lam_eff = lam * (1.0 - pb)
    L = sum(k * pk[k] for k in range(K + 1))
    Lq = sum((k - c) * pk[k] for k in range(c + 1, K + 1))
    W = L / lam_eff if lam_eff > 0 else 0.0
    Wq = Lq / lam_eff if lam_eff > 0 else 0.0
    return {
        "stable": True,
        "rho": rho,
        "pb": pb,
        "drop_rate": pb,
        "L": L,
        "Lq": Lq,
        "W": W,
        "Wq": Wq,
        "throughput": lam_eff
    }


def network_pipeline_theory(
    lam: float,
    mu_io: float,
    mu_cpu: float,
    mu_printer: float,
    mu_disk: float,
    p_printer: float = 0.3,
    p_disk: float = 0.7
) -> Dict[str, Any]:
    """GIẢI TÍCH MẠNG HÀNG ĐỢI MỞ THEO ĐỊNH LÝ JACKSON (Hình 1 đề bài).
    
    Theo định lý Jackson: Trong mạng mở dòng Poisson, mỗi nút trạm hành xử
    độc lập như một hệ M/M/1 với tốc độ đến cục bộ:
    - lambda_io = lambda
    - lambda_cpu = lambda
    - lambda_printer = lambda * p_printer (30%)
    - lambda_disk = lambda * p_disk (70%)
    
    Tổng độ trễ toàn trình (End-to-End Latency):
        W_total = W_io + W_cpu + p_printer * W_printer + p_disk * W_disk
    Nút cổ chai (Bottleneck Node) = Nút có rho_i = lambda_i / mu_i lớn nhất.
    """
    lam_io = lam
    lam_cpu = lam
    lam_printer = lam * p_printer
    lam_disk = lam * p_disk

    res_io = mm1_theory(lam_io, mu_io)
    res_cpu = mm1_theory(lam_cpu, mu_cpu)
    res_printer = mm1_theory(lam_printer, mu_printer)
    res_disk = mm1_theory(lam_disk, mu_disk)

    all_stable = (res_io["stable"] and res_cpu["stable"] and 
                  res_printer["stable"] and res_disk["stable"])

    nodes = {
        "io": res_io,
        "cpu": res_cpu,
        "printer": res_printer,
        "disk": res_disk
    }

    # Tìm nút cổ chai có hệ số sử dụng rho cao nhất
    bottleneck_node = max(nodes.keys(), key=lambda k: nodes[k]["rho"])
    bottleneck_rho = nodes[bottleneck_node]["rho"]

    if all_stable:
        total_W = (res_io["W"] + res_cpu["W"] + 
                   p_printer * res_printer["W"] + p_disk * res_disk["W"])
        total_L = lam * total_W
    else:
        total_W = float("inf")
        total_L = float("inf")

    return {
        "stable": all_stable,
        "nodes": nodes,
        "bottleneck_node": bottleneck_node,
        "bottleneck_rho": bottleneck_rho,
        "total_W": total_W,
        "total_L": total_L,
        "throughput": lam if all_stable else None
    }
