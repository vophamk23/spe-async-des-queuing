# 📖 HƯỚNG DẪN KIỂM THỬ VÀ VẬN HÀNH BỘ MÔ PHỎNG HÀNG ĐỢI (DES)
## BÀI TẬP LỚN MÔN ĐÁNH GIÁ HIỆU NĂNG HỆ THỐNG (CO3007) - HK261
**Trường Đại học Bách Khoa - ĐHQG TP.HCM**  
**Khoa Khoa học & Kỹ thuật Máy tính**  
**Nhóm thực hiện:** `SPE-L0x-008` (Lớp L02)  
**Giảng viên hướng dẫn:** Thầy Nguyễn Phương Duy  
**Đặc tả đề bài chính thức:** `hk261_BKsyspeEvsim.pdf`  

---

## 📑 MỤC LỤC
1. [Giới thiệu Dự án & Mục tiêu Nghiên cứu](#1-giới-thiệu-dự-án--mục-tiêu-nghiên-cứu)
2. [Cấu trúc Thư mục Đã Chuẩn hóa (`bkitevsim`)](#2-cấu-trúc-thư-mục-đã-chuẩn-hóa-bkitevsim)
3. [Cài đặt Môi trường (Installation & Prerequisites)](#3-cài-đặt-môi-trường-installation--prerequisites)
4. [Hướng dẫn Kiểm thử Toàn diện (5 Tầng Thực nghiệm)](#4-hướng-dẫn-kiểm-thử-toàn-diện-5-tầng-thực-nghiệm)
   - [Tầng 1: Kiểm thử Đơn vị & Khung Chuẩn của Thầy (31 Tests PASSED)](#tầng-1-kiểm-thử-đơn-vị--khung-chuẩn-của-thầy-20-tests-passed)
   - [Tầng 2: Kiểm thử Nhanh Từng Mô hình Hàng đợi (Sanity Checks - Tải nhẹ)](#tầng-2-kiểm-thử-nhanh-từng-mô-hình-hàng-đợi-sanity-checks---tải-nhẹ)
   - [Tầng 3: Kiểm thử Thẩm định Lý thuyết (Validation Sweeps - Tải trung bình)](#tầng-3-kiểm-thử-thẩm-định-lý-thuyết-validation-sweeps---tải-trung-bình)
   - [Tầng 4: Kiểm thử Tải nặng & Điểm nghẽn Cổ chai (Stress Testing & Bottleneck)](#tầng-4-kiểm-thử-tải-nặng--điểm-nghẽn-cổ-chai-stress-testing--bottleneck)
   - [Tầng 5: Chạy Tự động Toàn bộ Thực nghiệm & Xuất Biểu đồ 300 DPI](#tầng-5-chạy-tự-động-toàn-bộ-thực-nghiệm--xuất-biểu-đồ-300-dpi)
5. [Hướng dẫn Biên dịch Báo cáo LaTeX (`report/`)](#5-hướng-dẫn-biên-dịch-báo-cáo-latex-report)
6. [Bảng Tra cứu Tham số Dòng lệnh (CLI Cheat Sheet)](#6-bảng-tra-cứu-tham-số-dòng-lệnh-cli-cheat-sheet)

---

## 1. Giới thiệu Dự án & Mục tiêu Nghiên cứu

Dự án này là bài tập lớn toàn diện môn **Đánh giá Hiệu năng Hệ thống (System Performance Evaluation - CO3007)**, thực hiện mô hình hóa và đánh giá theo chuẩn khung kiến trúc `bkitevsim` được công bố trong tài liệu `hk261_BKsyspeEvsim.pdf`:

1. **Bộ máy Mô phỏng Sự kiện Rời rạc (DES Core Engine):**
   - Quản lý đồng hồ thời gian ảo (*Virtual Simulation Time*) độc lập hoàn toàn với thời gian thực đồng hồ (*Wall-clock Time*).
   - Hàng đợi sự kiện ưu tiên hiệu năng cao (*Priority Event Queue*): Cung cấp cả `MinHeapPriorityQueue` $\mathcal{O}(\log N)$ và `LadderQueue` $\mathcal{O}(1)$ phân tầng chống suy thoái hiệu năng khi có hàng triệu sự kiện.
   - Kiến trúc Tiến trình Logic (*Logical Processes - LPs*): Lớp cơ sở `BkSysLogicalProcess` hiện thực đầy đủ 4 hàm vòng đời: `initialize()`, `finalize()`, `elapse_virt_time()`, và `register_handler()`.

2. **Phối hợp Tác vụ Bất đồng bộ (`asyncio`):**
   - Ứng dụng mô hình truyền thông phi nghẽn (*non-blocking messaging*) thông qua `asyncio.Future` (Promise/Future pattern).
   - Quản lý vòng đời tiến trình mô phỏng song hành bằng `BkSysCoLogicalProcess` và `BkSysCoEventLoop` kết hợp `asyncio.TaskGroup`, `asyncio.gather`, và `asyncio.Runner` chuẩn Python 3.11+.

3. **Hiện thực Đầy đủ 6 Mô hình Hàng đợi Kendall Chuẩn:**
   - $M/M/1$: Đơn server, hàng đợi vô hạn.
   - $M/M/1/K$: Đơn server, bộ đệm hữu hạn dung lượng $K$, khảo sát hiện tượng rớt gói và mất mát dữ liệu.
   - $M/M/\infty$: Vô hạn server, mô hình trễ thuần túy (pure delay), không có hàng đợi.
   - $M/M/n/n$: Hệ thống mất gói Erlang (Erlang loss system), kiểm định công thức giải tích Erlang-B.
   - $M/M/c$: Đa server song song ($c \ge 2$), bộ đệm vô hạn, kiểm định công thức trễ Erlang-C.
   - $M/M/c/K$: Đa server song song kết hợp bộ đệm hữu hạn dung lượng tổng $K$.

4. **Mô phỏng Mạng Hàng đợi Đa chặng (Hình 1 đề bài):**
   - Mô phỏng chuỗi: $	ext{Source} 	o 	ext{I/O} 	o 	ext{CPU} 	o (	ext{Printer } 30\% / 	ext{Disk } 70\%) 	o 	ext{Sink}$.
   - Đo lường và nhận diện điểm nghẽn cổ chai (*Bottleneck Identification*) dựa trên định lý mạng Jackson.

---

## 2. Cấu trúc Thư mục Đã Chuẩn hóa (`bkitevsim`)

Toàn bộ mã nguồn cũ trong `src/` đã được **loại bỏ hoàn toàn**. Dự án được tái cấu trúc khớp 100% với tài liệu của giảng viên:

```text
BTL_DanhGiaHieuNangHeThong/
│
├── run_test.bat                             # Menu tương tác tự động chạy 31 test & mô phỏng
├── README.md                                # Tài liệu kỹ thuật dự án
├── HUONG_DAN_SU_DUNG_VA_KIEM_THU.md         # File này: Cẩm nang hướng dẫn kiểm thử chi tiết từ A-Z
├── hk261_BKsyspeEvsim.pdf                   # Đề bài cập nhật chính thức của thầy
├── pe4-single-queue_p1.pdf                  # Đề bài giai đoạn 1
├── Spe-Ass-Spec-SPE-L0x-008.pdf             # File báo cáo PDF chính thức nộp bài
│
├── report/                                  # BÁO CÁO HỌC THUẬT LATEX & PDF
│   ├── cover.tex                            # Trang bìa chuẩn ĐHBK (khung đôi TikZ, logo, 9 thành viên)
│   ├── main.tex                             # File LaTeX chủ đạo (quy trình 10 bước Raj Jain)
│   ├── main.pdf                             # Bản PDF báo cáo đã biên dịch hoàn chỉnh
│   ├── image/                               # Thư mục hình ảnh & logo trường
│   │   ├── hcmut.png                        # Logo chính thức ĐH Bách Khoa TP.HCM
│   │   ├── fsm_queue_server_uml.png         # Sơ đồ FSM máy trạng thái phục vụ của QueueServerLP
│   │   ├── uml_class_diagram.png            # Sơ đồ lớp UML 16 classes
│   │   └── uml_sequence_diagram.png         # Sơ đồ tuần tự UML
│   └── sections/                            # 5 chương nội dung chi tiết & bảng phân công
│       ├── assignment.tex                   # Bảng phân công nhiệm vụ cụ thể cho 9 thành viên
│       ├── 01_tong_quan.tex                 # Chương 1: Tổng quan, mục tiêu, KPIs, tham số & yếu tố
│       ├── 02_kien_truc.tex                 # Chương 2: Kiến trúc hệ thống, DES Engine, asyncio & UML Class
│       ├── 03_hien_thuc.tex                 # Chương 3: Hiện thực thuật toán, quản lý sự kiện & Future
│       ├── 04_thuc_nghiem.tex               # Chương 4: Kịch bản thử nghiệm, Verification & Validation
│       └── 05_ket_luan.tex                  # Chương 5: Đánh giá, kết luận & hướng phát triển
│
└── simulator/                               # BỘ MÁY MÔ PHỎNG PYTHON (chuẩn bkitevsim)
    ├── main.py                              # Entrypoint giao diện dòng lệnh (CLI) linh hoạt
    ├── requirements.txt                     # Danh sách thư viện phụ thuộc (numpy, scipy, matplotlib, pytest)
    ├── pytest.ini                           # Cấu hình test runner cho pytest
    ├── run_test.bat                         # Menu điều khiển chạy trực tiếp trong thư mục simulator
    ├── README.md                            # Tài liệu kỹ thuật chi tiết của simulator
    │
    ├── bkitevsim/                           # GÓI MÃ NGUỒN CHÍNH THỨC CỦA ĐỀ BÀI
    │   ├── core/                            # TẦNG LÕI MÔ PHỎNG SỰ KIỆN RỜI RẠC
    │   │   ├── event.py                     # Event dataclass, factory create_event(), strict ordering & EventType
    │   │   ├── logical_process.py           # BkSysLogicalProcess (4 hàm vòng đời: initialize, finalize,
    │   │   │                                #                      elapse_virt_time, register_handler)
    │   │   │                                # & BkSysLogicalProcessState (checkpointing / rollback)
    │   │   ├── logical_coProcess.py         # BkSysCoLogicalProcess, BkSysCoEventLoop, BkSysFuture
    │   │   ├── priority_queue.py            # BaseEventQueue, MinHeapPriorityQueue O(log N), LadderQueue O(1)
    │   │   ├── simulation.py                # Simulation (Giao diện Façade cấp cao) & SimulationOptions
    │   │   └── dispatcher.py                # Dispatcher bridge alias
    │   │
    │   ├── dispatchers/                     # BỘ ĐIỀU PHỐI SỰ KIỆN DES
    │   │   └── sequential_eventdispatcher.py# SequentialEventDispatcher & DistributedEventDispatcher
    │   │
    │   ├── models/                          # TẦNG NGHIỆP VỤ HÀNG ĐỢI
    │   │   ├── single_queue.py              # Job, SourceLP, QueueServerLP (Hợp nhất 6 hệ Kendall A/S/c/K), SinkLP
    │   │   └── network.py                   # BranchingServerLP (rẽ nhánh xác suất), NetworkSinkLP, QueuingNetwork
    │   │
    │   ├── async_engine/                    # TẦNG ĐIỀU PHỐI BẤT ĐỒNG BỘ ASYNCIO
    │   │   ├── future_manager.py            # AsyncFutureManager (Promise/Future pattern)
    │   │   └── task_coordinator.py         # TaskGroup, gather, as_completed, Runner
    │   │
    │   └── utils/                           # CÔNG CỤ TOÁN HỌC & ĐO ĐẠC THỐNG KÊ
    │       ├── theory.py                    # Nghiệm giải tích: Little, Erlang-B, Erlang-C, Jackson
    │       ├── metrics.py                   # Bộ đo tích phân Riemann thời gian (L, Lq, rho), CI 95%
    │       └── visualizer.py                # Tự động vẽ và xuất biểu đồ 300 DPI
    │
    ├── experiments/                         # KỊCH BẢN THỰC NGHIỆM
    │   └── run_all_experiments.py           # Chạy quét tham số tự động và xuất cả 4 đồ thị 300 DPI
    │
    ├── tests/                               # BỘ KIỂM THỬ TỰ ĐỘNG (31 TESTS PASSED)
    │   ├── test_verification.py             # 8 bài test kiểm chứng lõi DES & thẩm định lý thuyết
    │   ├── test_bkitevsim_framework.py      # 6 bài test kiểm định toàn diện chuẩn khung bkitevsim
    │   └── test_async_engine.py             # 6 bài test kiểm chứng tầng bất đồng bộ asyncio
    │
    └── plots/                               # Nơi lưu trữ ảnh đồ thị kết xuất từ experiments
```

---

## 3. Cài đặt Môi trường (Installation & Prerequisites)

### 3.1. Yêu cầu hệ thống
- **Hệ điều hành:** Windows 10/11, Ubuntu/Debian Linux, hoặc macOS.
- **Python:** Phiên bản `3.11` trở lên (đặc biệt khuyến nghị Python 3.12 để tận dụng tối đa `asyncio.TaskGroup` và `asyncio.Runner`).
- **LaTeX (nếu muốn tự biên dịch báo cáo):** MiKTeX hoặc TeX Live đầy đủ gói `vntex`, `geometry`, `tcolorbox`, `tikz`.

### 3.2. Cài đặt các gói thư viện Python
Mở PowerShell (Windows) hoặc Terminal (Linux/macOS) và thực hiện:

```bash
# Di chuyển vào thư mục simulator
cd simulator

# Cài đặt các gói phụ thuộc
pip install -r requirements.txt
```

Nội dung các gói phụ thuộc trong `requirements.txt`:
- `numpy`: Xử lý mảng số học, tính trung bình và phân phối ngẫu nhiên.
- `scipy`: Phân phối Student's t để tính khoảng tin cậy 95% ($CI_{95\%}$).
- `matplotlib`: Vẽ biểu đồ chuẩn báo cáo khoa học với độ phân giải cao 300 DPI.
- `pytest`: Bộ khung chạy kiểm thử tự động (*Verification Test Suite*).

---

## 4. Hướng dẫn Kiểm thử Toàn diện (5 Tầng Thực nghiệm)

### ⚡ CÁCH NHANH NHẤT: Sử dụng Menu Điều khiển Tự động (`run_test.bat`)
Nhóm đã phát triển sẵn file thực thi menu một chạm **`run_test.bat`** ngay tại thư mục gốc:
* **Chỉ cần nhấp đúp chuột vào file `run_test.bat`** (hoặc gõ `.
un_test.bat` từ terminal).
* Gõ số từ `1` đến `9` để chạy bất kỳ bài test nào mà không cần nhớ dòng lệnh dài:
  * `[1]`: Chạy toàn bộ **31 bài unit test tự động** (Verification, bkitevsim Framework & Async Engine).
  * `[2]`: Chạy mô phỏng $M/M/1$ ($\lambda=8$, $\mu=10$).
  * `[3]`: Chạy mô phỏng $M/M/1/K$ (đệm $K=5$, khảo sát rớt gói).
  * `[4]`: Chạy mô phỏng đa server $M/M/c$ ($c=3$).
  * `[5]`: Chạy mô phỏng mất gói $M/M/n/n$ (đối chiếu Erlang-B).
  * `[6]`: Chạy mạng hàng đợi đa chặng (Hình 1 đề bài, tìm nút cổ chai).
  * `[7]`: Chạy tự động toàn bộ 4 bài thực nghiệm & xuất 4 biểu đồ 300 DPI vào `plots/`.
  * `[8]`: Tự động biên dịch Báo cáo LaTeX sang PDF (`report/main.pdf`).
  * `[9]`: Chạy toàn bộ 31 bài test và **Tự động xuất File Excel thống kê đầy đủ (`BaoCao_KetQua_KiemThu.xlsx`)** gồm 3 Sheet: Dashboard, Chi tiết 31 Test Cases, và Đối chuẩn Giải tích lý thuyết với 67 chỉ số chuyên sâu.

Nếu muốn chạy thủ công bằng dòng lệnh, hãy di chuyển vào thư mục `simulator/`:
```bash
cd simulator
```

---

### Tầng 1: Kiểm thử Đơn vị & Khung Chuẩn của Thầy (31 Tests PASSED)
> **Mục tiêu:** Trả lời câu hỏi *"Are we building the system right?"* theo chuẩn Raj Jain. Kiểm tra hàng đợi ưu tiên không vi phạm thứ tự thời gian, sự kiện không bị mất mát, bảo toàn luồng lưu lượng ($N_{arrived} = N_{completed} + N_{in\_system} + N_{dropped}$ đạt sai số tuyệt đối bằng 0), cơ chế bất đồng bộ `asyncio` chuẩn mực, và các lớp của `bkitevsim` tuân thủ đúng API của thầy.

Chạy toàn bộ **31 ca kiểm thử tự động** bằng `pytest`:
```bash
pytest -v
```

**Kết quả thực tế (31/31 PASSED — 100% Xanh trong 7.3s):**
```text
tests/test_async_engine.py::test_future_manager_create_and_resolve PASSED          [  3%]
tests/test_async_engine.py::test_task_coordinator_gather PASSED                  [  6%]
tests/test_async_engine.py::test_task_coordinator_task_group PASSED              [  9%]
tests/test_async_engine.py::test_task_coordinator_as_completed PASSED            [ 12%]
tests/test_async_engine.py::test_task_coordinator_runner PASSED                  [ 16%]
tests/test_async_engine.py::test_sink_lp_resolves_future PASSED                  [ 19%]
tests/test_async_engine.py::test_future_manager_exception_and_cancellation PASSED [ 22%]
tests/test_async_engine.py::test_future_manager_timeout_handling PASSED          [ 25%]
tests/test_bkitevsim_framework.py::test_simulation_options PASSED                [ 29%]
tests/test_bkitevsim_framework.py::test_event_validation_and_factory PASSED     [ 32%]
tests/test_bkitevsim_framework.py::test_logical_process_lifecycle PASSED         [ 35%]
tests/test_bkitevsim_framework.py::test_simulation_facade_mm1_sequential PASSED [ 38%]
tests/test_bkitevsim_framework.py::test_simulation_facade_distributed_dispatcher PASSED [ 41%]
tests/test_bkitevsim_framework.py::test_coroutine_logical_process_and_event_loop PASSED [ 45%]
tests/test_bkitevsim_framework.py::test_ladder_queue_high_volume_stress PASSED   [ 48%]
tests/test_bkitevsim_framework.py::test_logical_process_custom_handlers PASSED   [ 51%]
tests/test_verification.py::test_priority_queue_monotonicity PASSED              [ 54%]
tests/test_verification.py::test_ladder_queue_consistency PASSED                 [ 58%]
tests/test_verification.py::test_event_conservation_law PASSED                   [ 61%]
tests/test_verification.py::test_causality_trace_analysis PASSED                 [ 64%]
tests/test_verification.py::test_mm1_validation_accuracy PASSED                  [ 67%]
tests/test_verification.py::test_erlang_b_loss_validation PASSED                 [ 70%]
tests/test_verification.py::test_queuing_network_connectivity PASSED             [ 74%]
tests/test_verification.py::test_queuing_network_jackson_validation PASSED       [ 77%]
tests/test_verification.py::test_mm1k_validation_accuracy PASSED                 [ 80%]
tests/test_verification.py::test_mmc_validation_accuracy PASSED                  [ 83%]
tests/test_verification.py::test_mminf_validation_accuracy PASSED                [ 87%]
tests/test_verification.py::test_mmck_validation_accuracy PASSED                 [ 90%]
tests/test_verification.py::test_littles_law_invariant PASSED                    [ 93%]
tests/test_verification.py::test_seed_reproducibility PASSED                     [ 96%]
tests/test_verification.py::test_exponential_workload_generator PASSED           [100%]
============================= 31 passed in 7.35s ==============================
```

---

### Tầng 2: Kiểm thử Nhanh Từng Mô hình Hàng đợi (Sanity Checks - Tải nhẹ)
> **Mục tiêu:** Chạy nhanh kiểm tra luồng hoạt động cơ bản của từng mô hình qua CLI với thời gian mô phỏng ngắn ($T_{sim} = 1000 - 2000$).

#### 1. Kiểm thử mô hình $M/M/1$ (Tải cân bằng $ \rho = 0.5$):
- $\lambda = 5.0, \mu = 10.0 \implies  \rho = 0.5$.
- Lý thuyết: $L = \frac{0.5}{1-0.5} = 1.0$, $W = \frac{1}{10-5} = 0.20$.
```bash
python main.py --model MM1 --lambda 5.0 --mu 10.0 --sim-time 2000
```

#### 2. Kiểm thử mô hình $M/M/1/K$ (Bộ đệm nhỏ $K=5$, quan sát rớt gói):
- $\lambda = 8.0, \mu = 10.0, K = 5$.
```bash
python main.py --model MM1K --lambda 8.0 --mu 10.0 --capacity 5 --sim-time 2000
```

#### 3. Kiểm thử mô hình vô hạn server $M/M/\infty$ (Pure Delay, không chờ đợi):
- Bất kỳ yêu cầu nào đến cũng được phục vụ ngay lập tức ($W_q = 0$).
```bash
python main.py --model MMINF --lambda 10.0 --mu 2.0 --sim-time 1000
```

#### 4. Kiểm thử mô hình mất gói Erlang $M/M/n/n$ ($n = 4$ kênh, không bộ đệm):
- Không có hàng chờ; yêu cầu đến khi đủ 4 máy bận sẽ bị từ chối ngay.
```bash
python main.py --model MMNN --lambda 12.0 --mu 4.0 --servers 4 --sim-time 2000
```

#### 5. Kiểm thử mô hình đa server $M/M/c$ ($c = 3$ máy chủ, đệm vô hạn):
- $c = 3, \mu = 5.0$ (tổng công suất phục vụ $c\mu = 15.0$), $\lambda = 10.0 \implies 
ho = 0.67$.
```bash
python main.py --model MMC --lambda 10.0 --mu 5.0 --servers 3 --sim-time 2000
```

#### 6. Kiểm thử mô hình đa server có bộ đệm $M/M/c/K$ ($c = 2, K = 6$):
- Hệ thống chứa tối đa 6 khách (2 đang phục vụ, 4 đang chờ).
```bash
python main.py --model MMCK --lambda 12.0 --mu 5.0 --servers 2 --capacity 6 --sim-time 2000
```

#### 7. Kiểm thử mạng hàng đợi (Queuing Network Topology - Tải nhẹ):
- Chạy chuỗi xử lý mạng gồm I/O-Device, CPU, Printer, Disk theo Hình 1 đề bài với tải nhẹ $\lambda = 2.0$:
```bash
python main.py --model network --lambda 2.0 --sim-time 2000
```

---

### Tầng 3: Kiểm thử Thẩm định Lý thuyết (Validation Sweeps - Tải trung bình)
> **Mục tiêu:** Trả lời câu hỏi *"Are we building the right system?"*. Chạy mô phỏng đủ lâu ($T_{sim} = 10{,}000$ đến $20{,}000$) để đạt trạng thái dừng (*steady-state*), so sánh đối chiếu định lượng số liệu mô phỏng với công thức giải tích cổ điển.

#### 1. Thẩm định mô hình $M/M/1$ qua định luật Little:
Chạy với $\lambda = 8.0, \mu = 10.0 \implies  \rho = 0.8$:
- Công thức lý thuyết: $W = \frac{1}{\mu - \lambda} = 0.50$, $L = \frac{\rho}{1-\rho} = 4.0$.
```bash
python main.py --model MM1 --lambda 8.0 --mu 10.0 --sim-time 15000
```
*Ghi nhận:* Sai số giữa mô phỏng và lý thuyết nhỏ hơn $1.5\%$.

#### 2. Thẩm định công thức Erlang-B trên hệ thống $M/M/n/n$:
Với $n = 5$ máy chủ, $\lambda = 10.0, \mu = 2.5 \implies a = \lambda/\mu = 4.0$ Erlangs:
- Công thức Erlang-B lý thuyết: $B(5, 4.0) \approx 0.2173$ ($21.73\%$).
```bash
python main.py --model MMNN --servers 5 --lambda 10.0 --mu 2.5 --sim-time 20000
```
*Ghi nhận:* Tỉ lệ rớt gói quan sát được trong mô phỏng xấp xỉ $21.5\% - 21.9\%$.

#### 3. Thẩm định cấu trúc hàng đợi ưu tiên tốc độ cao `LadderQueue`:
So sánh tính nhất quán khi chuyển đổi giữa hàng đợi `MinHeap` chuẩn và `LadderQueue` $\mathcal{O}(1)$:
```bash
python main.py --model MM1 --lambda 7.0 --mu 10.0 --sim-time 10000 --ladder-queue
```

---

### Tầng 4: Kiểm thử Tải nặng & Điểm nghẽn Cổ chai (Stress Testing & Bottleneck)
> **Mục tiêu:** Khảo sát các trường hợp khắc nghiệt nhất: tiệm cận bão hòa ($
ho 	o 1.0$), quá tải tràn trề ($ \rho > 1.0$), kiểm tra hiện tượng bùng nổ độ trễ (*Latency Explosion*) và hiệu ứng *Bufferbloat*.

#### 1. Thử nghiệm Tiệm cận Bão hòa ($ \rho = 0.95$ - Tải cực nặng):
- $\lambda = 9.5, \mu = 10.0 \implies  \rho = 0.95$.
- Lý thuyết: $L = \frac{0.95}{1 - 0.95} = 19.0$, $W = \frac{1}{0.5} = 2.0$ (tăng gấp 10 lần so với lúc tải 0.5).
```bash
python main.py --model MM1 --lambda 9.5 --mu 10.0 --sim-time 30000
```
*Hiện tượng quan sát:* Thời gian chờ tăng phi tuyến tính theo đúng hàm tiệm cận $1/(1-\rho)$.

#### 2. Thử nghiệm Quá tải trên Hàng đợi Hữu hạn ($ \rho = 1.5 > 1.0$ - Tải vượt công suất phục vụ):
- $\lambda = 15.0, \mu = 10.0$, bộ đệm hạn chế $K = 10$.
```bash
python main.py --model MM1K --lambda 15.0 --mu 10.0 --capacity 10 --sim-time 15000
```
*Hiện tượng quan sát:* Hệ thống không thể xử lý kịp lưu lượng vào, tỉ lệ dropped packets tăng vọt lên xấp xỉ $pprox 33.3\%$. Chiều dài hàng đợi luôn bão hòa ở mức $K = 10$.

#### 3. Thử nghiệm Hiện tượng Bufferbloat ($K$ lớn dưới tải cao):
- Cùng mức tải cao $\lambda = 9.0, \mu = 10.0$, so sánh giữa $K = 5$ và $K = 50$:
```bash
# Bộ đệm nhỏ: Rớt gói nhẹ nhưng độ trễ cực thấp
python main.py --model MM1K --lambda 9.0 --mu 10.0 --capacity 5 --sim-time 15000

# Bộ đệm khổng lồ: Mất gói = 0 nhưng độ trễ bùng nổ (Bufferbloat)
python main.py --model MM1K --lambda 9.0 --mu 10.0 --capacity 50 --sim-time 15000
```

#### 4. Thử nghiệm Nút thắt Cổ chai Mạng (Network Bottleneck Stress Test):
Mạng có 4 nút với tốc độ xử lý:
- I/O-Device: $\mu_1 = 8.0$
- CPU: $\mu_2 = 10.0$
- Printer: $\mu_3 = 4.0$ (nhận $30\%$ lưu lượng từ CPU)
- Disk: $\mu_4 = 6.0$ (nhận $70\%$ lưu lượng từ CPU)

Khi tăng tốc độ tải từ nguồn $\lambda = 3.5$:
```bash
python main.py --model network --lambda 3.5 --sim-time 20000
```
*Hiện tượng quan sát:* Nút **I/O Device** chính là nút thắt cổ chai (*Bottleneck*, $
ho = 43.8\%$) hạn chế thông lượng của toàn mạng!

---

### Tầng 5: Chạy Tự động Toàn bộ Thực nghiệm & Xuất Biểu đồ 300 DPI
> **Mục tiêu:** Tự động hóa hoàn toàn quy trình đo đạc thực nghiệm (Replication, Monte Carlo, Quét tham số, Tính khoảng tin cậy 95%, và Xuất 4 biểu đồ báo cáo khoa học).

Thực hiện lệnh:
```bash
python experiments/run_all_experiments.py
```

**Quá trình thực thi:**
1. **Experiment 1 ($M/M/1$):** Quét 8 mức tải $
ho \in [0.1, 0.95]$, mỗi điểm chạy 5 hạt giống ngẫu nhiên độc lập $\implies$ Xuất biểu đồ `plots/mm1_response_time_validation.png`.
2. **Experiment 2 ($M/M/1/K$):** Quét các dung lượng đệm $K \in \{3, 5, 8, 12, 20, 30, 50\}$ $\implies$ Xuất biểu đồ `plots/mm1k_buffer_tradeoff.png`.
3. **Experiment 3 ($M/M/n/n$ Erlang-B):** Khảo sát hệ thống mất gói với tải Erlang thay đổi từ $1$ đến $10$ $\implies$ Xuất biểu đồ `plots/erlang_b_validation.png`.
4. **Experiment 4 (Queuing Network Bottleneck):** Nhận diện nút thắt cổ chai với $\lambda = 3.5$, theo dõi hệ số sử dụng của cả 4 nút (I/O, CPU, Printer, Disk) $\implies$ Xuất biểu đồ `plots/network_bottleneck_analysis.png`.

Toàn bộ 4 file ảnh đồ thị sẽ tự động được tạo mới trong thư mục `plots/` với chuẩn 300 DPI sẵn sàng đưa vào báo cáo LaTeX.

---


---

### Tầng 6: Hệ thống Kiểm thử Tự động & Xuất Bộ đôi File Excel Chuẩn Doanh nghiệp

Hệ thống cung cấp kiến trúc kiểm thử hướng dữ liệu (**Data-Driven Testing - DDT**) gồm **2 bộ file Excel độc lập** được đồng bộ tự động:

```text
BTL_DanhGiaHieuNangHeThong/
├── DanhSach_TestCases_Input.xlsx      # [FILE 1: ĐẦU VÀO ĐỂ TEST] Đặc tả kịch bản, tham số & kỳ vọng
└── BaoCao_KetQua_KiemThu.xlsx         # [FILE 2: KẾT QUẢ THỰC THI] Dashboard, biểu đồ & thống kê kết quả
```
*(Bản sao cũng được lưu đồng thời trong thư mục `simulator/` để thuận tiện truy cập).*

#### 1. File 1: `DanhSach_TestCases_Input.xlsx` (Bảng Đặc Tả Kịch Bản Đầu Vào - Test Specification)
* **Mục đích:** Là tài liệu **để test** chính thức cho Kỹ sư QA hoặc Giảng viên xem xét, phê duyệt và tùy biến tham số trước khi mô phỏng.
* **Cấu trúc 3 Sheet chuyên nghiệp:**
  1. `📖 Hướng dẫn & Quy trình Test`: Tóm tắt 4 thẻ KPI tổng quan, quy trình V&V 10 bước của Giáo sư Raj Jain, và hướng dẫn vận hành kiểm thử hướng dữ liệu.
  2. `🧪 31 Test Cases (Đầu vào)`: Định nghĩa chi tiết 31 ca kiểm thử với **12 cột đặc tả**: *STT, Mã Test Case, Phân nhóm chức năng, Tên hàm Pytest, Thành phần kiểm thử, Mục tiêu kiểm thử, Tiền điều kiện (Preconditions), Các bước thực hiện (Test Steps), Dữ liệu & Tham số đầu vào, Kết quả kỳ vọng, Tiêu chí nghiệm thu, Độ ưu tiên (Critical / High / Normal)*.
  3. `📐 67 Đối chuẩn (Đầu vào)`: Định nghĩa đầy đủ 67 kịch bản mô phỏng đối chuẩn qua 6 mô hình Kendall và mạng Jackson với **13 cột tham số**: *STT, Tên mô hình, Kịch bản & mức tải, lambda, mu, c, K, Tsim, Chỉ số kiểm chứng, Giá trị lý thuyết chuẩn (Benchmark), Đơn vị, Ngưỡng sai số (RE <= 5.0%), Công thức giải tích áp dụng*.

#### 2. File 2: `BaoCao_KetQua_KiemThu.xlsx` (Báo Cáo Kết QuẢ Thực Thi - Execution Report)
* **Mục đích:** Là báo cáo kết quả thực thi tự động, ghi nhận số liệu đo đạc thực tế, thời gian chạy và đối chuẩn giải tích.
* **Định dạng mỹ thuật hiện đại (Corporate Dashboard Aesthetics):**
  1. `📊 Dashboard & Tổng quan`:
     - **8 Thẻ KPI tổng quan cao cấp:** Tổng số test (31), Đạt (31), Lỗi (0), Tỷ lệ thành công (100.0%), Số kịch bản đối chuẩn (67), Đạt hội tụ (67/67), Sai số trung bình (1.06%), Sai số tối đa (4.47% < 5.0%).
     - **Bảng Thông tin phiên kiểm thử:** Thời gian, công cụ test runner, OS, tiêu chuẩn nghiệm thu.
     - **Bảng Tổng hợp theo phân nhóm chức năng:** Tầng Async (8/8), Khung chuẩn bkitevsim (8/8), Kiểm chứng DES (15/15), Tổng cộng 31/31.
     - **2 Biểu đồ đồ họa trực quan (Native OpenPyXL Charts):** Biểu đồ Cột (Bar Chart) phân bổ test cases theo nhóm và Biểu đồ Tròn (Pie Chart) biểu thị tỷ lệ Đạt chuẩn 100% Pass Rate.
  2. `🧪 Chi tiết 31 Test Cases`: Bảng kết quả chạy thực tế với thời gian thực thi từng test (mili-giây), Huy hiệu trạng thái mềm mại (`PASSED` xanh lá pastel `#DCFCE7`, `ĐẠT CHUẨN`), cố định tiêu đề (`Freeze Panes A2`), và bộ lọc (`AutoFilter`).
  3. `📐 Đối chuẩn Lý thuyết`: So sánh 67 cặp giá trị giữa **Nghiệm giải tích (Theory)** và **Kết quả mô phỏng (Simulated)**, sai số tương đối $RE < 5\%$, định dạng số 4 chữ số thập phân (`0.0000`), và trạng thái `ĐẠT (HỘI TỤ)`.

#### Cách chạy tự động cập nhật cả 2 file:
- **Cách 1 (Menu một chạm):** Chạy `run_test.bat`, nhấn phím `[9]`.
- **Cách 2 (CLI):**
  ```bash
  cd simulator
  python run_tests_to_excel.py
  ```

## 5. Hướng dẫn Biên dịch Báo cáo LaTeX (`report/`)

### 5.1. Biên dịch trên máy tính cá nhân (Local với MiKTeX hoặc TeX Live)
Di chuyển vào thư mục `report/`:
```bash
cd report
```

Thực hiện biên dịch tài liệu bằng lệnh `pdflatex`:
```bash
# Biên dịch lần 1 (khởi tạo bảng mục lục và tham chiếu)
pdflatex -interaction=nonstopmode main.tex

# Biên dịch lần 2 (cập nhật chính xác số trang LastPage và bảng mục lục)
pdflatex -interaction=nonstopmode main.tex
```

File báo cáo PDF hoàn chỉnh sẽ được ghi đè vào: `report/main.pdf`.

### 5.2. Chỉnh sửa và làm việc trên Overleaf
Nếu nhóm muốn cộng tác trực tuyến trên nền tảng Overleaf:
1. Nén toàn bộ thư mục `report/` thành file `.zip`.
2. Truy cập [Overleaf.com](https://www.overleaf.com), chọn **New Project** $	o$ **Upload Project**.
3. Tải file `.zip` vừa nén lên.
4. Đảm bảo cấu hình trình biên dịch của Overleaf là **pdfLaTeX** và file chính là `main.tex`.

---

## 6. Bảng Tra cứu Tham số Dòng lệnh (CLI Cheat Sheet)

| Cờ lệnh (Option) | Kiểu dữ liệu | Giá trị mặc định | Giải thích chi tiết |
| :--- | :---: | :---: | :--- |
| `--model` | Chuỗi | `MM1` | Loại mô hình hàng đợi: `MM1`, `MM1K`, `MMINF`, `MMNN`, `MMC`, `MMCK`, `network` |
| `--lambda` | Số thực | `8.0` | Tốc độ yêu cầu đến trung bình $\lambda$ (Poisson arrival rate) |
| `--mu` | Số thực | `10.0` | Tốc độ phục vụ trung bình $\mu$ của mỗi server (Exponential service rate) |
| `--servers` | Số nguyên | `1` | Số lượng máy chủ song song ($c$ hoặc $n$) trong các mô hình $M/M/c$, $M/M/n/n$, $M/M/c/K$ |
| `--capacity` | Số nguyên | `10` | Sức chứa tối đa của hệ thống ($K$) trong các mô hình $M/M/1/K$, $M/M/c/K$ |
| `--sim-time` | Số thực | `5000.0` | Tổng thời gian ảo mô phỏng ($T_{sim}$) |
| `--replications` | Số nguyên | `5` | Số lượt lặp độc lập để tính khoảng tin cậy 95% theo Student-t |
| `--ladder-queue` | Cờ logic | `False` | Bật bộ lập lịch LadderQueue $\mathcal{O}(1)$ thay cho MinHeap $\mathcal{O}(\log N)$ |

---
*Tài liệu được phát triển và chuẩn hóa phục vụ BTL môn Đánh giá Hiệu năng Hệ thống - HK261 - Trường Đại học Bách Khoa TP.HCM.*
