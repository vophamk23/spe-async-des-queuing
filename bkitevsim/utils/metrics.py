import math
from typing import Dict, List, Optional
from scipy import stats


class MetricsCollector:
    """BỘ THU THẬP VÀ TÍNH TOÁN CÁC CHỈ SỐ HIỆU NĂNG HÀNG ĐỢI (Performance Metrics).
    
    Phân biệt rõ ràng 2 phương pháp đo lường trong lý thuyết mô phỏng:
    1. Trung bình theo mẫu (Sample-averaged metrics):
       - W (Response time): Thời gian toàn trình từ lúc đến đến lúc rời đi.
       - Wq (Wait time): Thời gian chờ đợi trong hàng đợi trước khi được phục vụ.
       - S (Service time): Thời gian server thực tế xử lý.
       => Tính bằng: Tổng thời gian / Tổng số khách hoàn thành.
    
    2. Trung bình theo thời gian (Time-integrated metrics):
       - L (Mean jobs in system): Số khách trung bình trong toàn hệ thống.
       - Lq (Mean jobs in queue): Số khách trung bình ngồi chờ ở hàng đợi.
       - rho (Utilization): Hệ số sử dụng trung bình của các máy chủ.
       => BẮT BUỘC TÍNH BẰNG TÍCH PHÂN DIỆN TÍCH: Area / sim_time.
    """
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.arrived_count: int = 0
        self.completed_count: int = 0
        self.dropped_count: int = 0

        self.waiting_times: List[float] = []
        self.service_times: List[float] = []
        self.response_times: List[float] = []

        # Các biến phục vụ tích phân thời gian (Time-integrated state tracking)
        self._last_state_change_time: float = 0.0
        self._current_q_len: int = 0
        self._current_in_sys: int = 0
        self._busy_servers: int = 0

        # Tích lũy diện tích hình chữ nhật: Area = sum(State * dt)
        self._area_q_len: float = 0.0
        self._area_in_sys: float = 0.0
        self._area_busy_servers: float = 0.0

    def update_state(
        self,
        current_time: float,
        q_len: Optional[int] = None,
        in_sys: Optional[int] = None,
        busy_servers: Optional[int] = None
    ) -> None:
        """TÍNH TÍCH PHÂN THỜI GIAN THEO DẠNG HÌNH CHỮ NHẬT:
        
        Khoảng thời gian vừa qua dt = current_time - last_time.
        Trong suốt khoảng dt này, trạng thái không đổi, vì vậy:
            Diện tích tích lũy += Trạng thái cũ * dt
        Sau đó mới cập nhật trạng thái mới cho mốc tiếp theo.
        """
        dt = current_time - self._last_state_change_time
        if dt > 0:
            self._area_q_len += self._current_q_len * dt
            self._area_in_sys += self._current_in_sys * dt
            self._area_busy_servers += self._busy_servers * dt
            self._last_state_change_time = current_time

        if q_len is not None:
            self._current_q_len = q_len
        if in_sys is not None:
            self._current_in_sys = in_sys
        if busy_servers is not None:
            self._busy_servers = busy_servers

    def record_arrival(self) -> None:
        """Đếm số yêu cầu đến."""
        self.arrived_count += 1

    def record_drop(self) -> None:
        """Đếm số yêu cầu bị rớt gói do đầy bộ đệm."""
        self.dropped_count += 1

    def record_completion(self, wait_time: float, serv_time: float) -> None:
        """Ghi nhận dữ liệu của một yêu cầu hoàn tất."""
        self.completed_count += 1
        self.waiting_times.append(wait_time)
        self.service_times.append(serv_time)
        self.response_times.append(wait_time + serv_time)

    def finalize(self, total_sim_time: float, num_servers: int = 1) -> Dict[str, float]:
        """TỔNG KẾT VÀ TÍNH TOÁN BỘ CHỈ SỐ CUỐI CÙNG CHO LƯỢT CHẠY."""
        # Chốt sổ diện tích tích phân đến mốc kết thúc mô phỏng
        self.update_state(total_sim_time)
        
        sim_time = max(total_sim_time, 1e-9)
        # 1. Trung bình mẫu
        avg_wait = (sum(self.waiting_times) / len(self.waiting_times)) if self.waiting_times else 0.0
        avg_resp = (sum(self.response_times) / len(self.response_times)) if self.response_times else 0.0
        avg_serv = (sum(self.service_times) / len(self.service_times)) if self.service_times else 0.0

        # 2. Thông lượng và tỉ lệ rơi gói
        throughput = self.completed_count / sim_time
        drop_rate = (self.dropped_count / self.arrived_count) if self.arrived_count > 0 else 0.0

        # 3. Trung bình theo thời gian (Chia diện tích tích lũy cho tổng thời gian)
        Lq = self._area_q_len / sim_time
        L = self._area_in_sys / sim_time
        rho = (self._area_busy_servers / (sim_time * num_servers)) if num_servers > 0 else 0.0

        return {
            "arrived": self.arrived_count,
            "completed": self.completed_count,
            "dropped": self.dropped_count,
            "throughput": throughput,
            "drop_rate": drop_rate,
            "W": avg_resp,
            "Wq": avg_wait,
            "S": avg_serv,
            "L": L,
            "Lq": Lq,
            "rho": rho,
            "sim_time": sim_time
        }


def compute_confidence_interval(samples: List[float], confidence: float = 0.95) -> Dict[str, float]:
    """TÍNH KHOẢNG TIN CẬY 95% THEO PHÂN PHỐI STUDENT'S T (Chuẩn Raj Jain).
    
    Công thức:
        Mean = sum(x) / n
        s = sqrt(sum((x - Mean)^2) / (n - 1))  # Độ lệch chuẩn mẫu
        std_err = s / sqrt(n)
        ci_half = t_{1 - alpha/2, n-1} * std_err
        Khoảng tin cậy: [Mean - ci_half, Mean + ci_half]
    """
    n = len(samples)
    if n == 0:
        return {"mean": 0.0, "ci_half": 0.0, "ci_low": 0.0, "ci_high": 0.0, "std": 0.0}
    if n == 1:
        return {"mean": samples[0], "ci_half": 0.0, "ci_low": samples[0], "ci_high": samples[0], "std": 0.0}

    mean = sum(samples) / n
    variance = sum((x - mean) ** 2 for x in samples) / (n - 1)
    std_dev = math.sqrt(variance)
    std_err = std_dev / math.sqrt(n)

    # Tra giá trị t tới hạn từ phân phối Student với bậc tự do df = n - 1
    alpha = 1.0 - confidence
    t_crit = stats.t.ppf(1.0 - (alpha / 2.0), df=n - 1)
    ci_half = t_crit * std_err

    return {
        "mean": mean,
        "std": std_dev,
        "ci_half": ci_half,
        "ci_low": mean - ci_half,
        "ci_high": mean + ci_half
    }


def compute_relative_error(simulation_val: float, analytical_val: float) -> float:
    """TÍNH SAI SỐ TƯƠNG ĐỐI PHẦN TRĂM (%):
    
    Công thức: |Simulation - Theory| / Theory * 100%
    """
    if abs(analytical_val) < 1e-9:
        return 0.0 if abs(simulation_val) < 1e-9 else 100.0
    return abs(simulation_val - analytical_val) / abs(analytical_val) * 100.0
