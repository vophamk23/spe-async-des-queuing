"""Build full input test case specification excel: DanhSach_TestCases_Input.xlsx"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Bảng màu thương hiệu (Corporate Modern Palette)
COLOR_PRIMARY = "1E3A8A"       # Deep Royal Navy
COLOR_SECONDARY = "0F766E"     # Deep Teal
COLOR_ZEBRA = "F8FAFC"         # Soft alternating gray
COLOR_BORDER = "CBD5E1"        # Slate Gray border
COLOR_HIGH = "FEF3C7"          # Soft Amber
COLOR_CRIT = "FEE2E2"          # Soft Red
COLOR_NORM = "E0F2FE"          # Soft Blue
COLOR_CARD_1 = "1E3A8A"        # Navy
COLOR_CARD_2 = "0F766E"        # Teal
COLOR_CARD_3 = "2563EB"        # Blue
COLOR_CARD_4 = "059669"        # Emerald

font_banner_title = Font(name="Segoe UI", size=15, bold=True, color="FFFFFF")
font_banner_sub = Font(name="Segoe UI", size=9, italic=True, color="E0E7FF")
font_sec_title = Font(name="Segoe UI", size=12, bold=True, color=COLOR_PRIMARY)
font_th = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
font_cell = Font(name="Segoe UI", size=9)
font_cell_bold = Font(name="Segoe UI", size=9, bold=True)
font_cell_code = Font(name="Consolas", size=9)
font_kpi_num = Font(name="Segoe UI", size=18, bold=True, color="FFFFFF")
font_kpi_lbl = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")

thin_border = Border(
    left=Side(style="thin", color=COLOR_BORDER),
    right=Side(style="thin", color=COLOR_BORDER),
    top=Side(style="thin", color=COLOR_BORDER),
    bottom=Side(style="thin", color=COLOR_BORDER),
)
header_border = Border(
    left=Side(style="thin", color="94A3B8"),
    right=Side(style="thin", color="94A3B8"),
    top=Side(style="medium", color=COLOR_PRIMARY),
    bottom=Side(style="medium", color=COLOR_PRIMARY),
)


def generate_input_specification_excel(target_paths=None):
    """Tạo file DanhSach_TestCases_Input.xlsx định dạng chuyên nghiệp chuẩn doanh nghiệp."""
    wb = openpyxl.Workbook()

    # ==============================================================================
    # SHEET 1: HƯỚNG DẪN & ĐẶC TẢ TEST PLAN
    # ==============================================================================
    ws_guide = wb.active
    ws_guide.title = "📖 Hướng dẫn & Quy trình Test"
    ws_guide.views.sheetView[0].showGridLines = True

    # Banner chính
    ws_guide.merge_cells("A1:G1")
    ws_guide.merge_cells("A2:G2")
    ws_guide["A1"] = "BẢNG ĐẶC TẢ KỊCH BẢN KIỂM THỬ ĐẦU VÀO (TEST CASE SPECIFICATION)"
    ws_guide["A2"] = "Hệ thống Mô phỏng Hàng đợi Sự kiện Rời rạc (DES) & Bất đồng bộ (CO3007) | Nhóm SPE-L0x-008"
    ws_guide["A1"].font = font_banner_title
    ws_guide["A2"].font = font_banner_sub
    ws_guide["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_guide["A2"].alignment = Alignment(horizontal="center", vertical="center")

    banner_fill = PatternFill(start_color=COLOR_PRIMARY, end_color=COLOR_PRIMARY, fill_type="solid")
    for r in range(1, 3):
        for c in range(1, 8):
            ws_guide.cell(row=r, column=c).fill = banner_fill

    ws_guide.row_dimensions[1].height = 32
    ws_guide.row_dimensions[2].height = 20

    # 4 KPI Overview Cards (Row 4 - 5)
    kpi_cards = [
        ("A", "B", "TỔNG SỐ TEST CASES", "31 Tests Đơn vị & Tích hợp", COLOR_CARD_1),
        ("C", "D", "KỊCH BẢN ĐỐI CHUẨN", "67 Scenarios (6 Mô hình)", COLOR_CARD_2),
        ("E", "F", "PHƯƠNG PHÁP NGHIỆM THU", "Raj Jain 10-Step V&V", COLOR_CARD_3),
        ("G", "G", "NGƯỠNG CHẤP NHẬN", "RE <= 5.0%", COLOR_CARD_4),
    ]

    for c_start, c_end, lbl, val, bg_hex in kpi_cards:
        c1, c2 = f"{c_start}4", f"{c_end}4"
        c3, c4 = f"{c_start}5", f"{c_end}5"
        if c_start != c_end:
            ws_guide.merge_cells(f"{c1}:{c2}")
            ws_guide.merge_cells(f"{c3}:{c4}")
        ws_guide[c1] = lbl
        ws_guide[c3] = val
        ws_guide[c1].font = font_kpi_lbl
        ws_guide[c3].font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        ws_guide[c1].alignment = Alignment(horizontal="center", vertical="center")
        ws_guide[c3].alignment = Alignment(horizontal="center", vertical="center")

        fill_k = PatternFill(start_color=bg_hex, end_color=bg_hex, fill_type="solid")
        for r in range(4, 6):
            col_s = ord(c_start) - ord('A') + 1
            col_e = ord(c_end) - ord('A') + 1
            for col in range(col_s, col_e + 1):
                ws_guide.cell(row=r, column=col).fill = fill_k

    ws_guide.row_dimensions[4].height = 18
    ws_guide.row_dimensions[5].height = 28

    guide_sections = [
        ("A7", "1. MỤC ĐÍCH VÀ PHẠM VI TÀI LIỆU TEST", [
            ("Phạm vi tài liệu:", "Tài liệu này là Bảng Đặc tả Kịch bản Kiểm thử Đầu vào (Test Specification / Test Plan) chính thức của dự án."),
            ("Đối tượng kiểm thử:", "Toàn bộ mã nguồn khung mô phỏng bkitevsim, tầng bất đồng bộ asyncio, 6 mô hình hàng đợi Kendall và mạng Jackson 4 trạm."),
            ("Tiêu chuẩn khoa học:", "Áp dụng phương pháp luận Verification & Validation (V&V) 10 bước của Giáo sư Raj Jain (Washington University)."),
        ]),
        ("A12", "2. CẤU TRÚC BỘ KIỂM THỬ TRONG FILE EXCEL NÀY", [
            ("Sheet 2 (🧪 31 Test Cases Đầu vào):", "Định nghĩa đầy đủ 31 ca kiểm thử đơn vị & tích hợp với Tiền điều kiện, Tham số đầu vào, Các bước thực hiện, Kết quả kỳ vọng và Ngưỡng chấp nhận."),
            ("Sheet 3 (📐 67 Đối chuẩn Đầu vào):", "Định nghĩa chi tiết 67 kịch bản mô phỏng đối chuẩn giải tích qua các mức tải trọng từ nhẹ (rho=0.3) đến quá tải (rho=1.4)."),
            ("Tính chất tùy biến:", "Kỹ sư hoặc Giảng viên có thể xem xét, chỉnh sửa tham số (lambda, mu, c, K, Tsim) trực tiếp trên file này trước khi chạy mô phỏng."),
        ]),
        ("A17", "3. HƯỚNG DẪN THỰC THI KIỂM THỬ & XUẤT BÁO CÁO KẾT QUẢ", [
            ("Cách 1 (Menu một chạm):", "Chạy file 'run_test.bat' ngay tại thư mục gốc, bấm phím [9] để tự động chạy và xuất báo cáo kết quả."),
            ("Cách 2 (Dòng lệnh CLI):", "Mở terminal tại thư mục 'simulator/' và chạy lệnh: python run_tests_to_excel.py"),
            ("Kết quả xuất ra:", "Sau khi chạy xong, kết quả thực thi thực tế (Thời gian mili-giây, Sai số %, Trạng thái PASSED/FAILED) sẽ được xuất sang file 'BaoCao_KetQua_KiemThu.xlsx'."),
        ]),
        ("A22", "4. QUY TRÌNH THỰC HIỆN KIỂM THỬ HƯỚNG DỮ LIỆU (DATA-DRIVEN TESTING)", [
            ("Bước 1 (Đặc tả):", "Xem và kiểm tra các tham số đầu vào trong Sheet 2 và Sheet 3 của file Excel này."),
            ("Bước 2 (Thực thi):", "Hệ thống test tự động đọc kịch bản, chạy mô phỏng DES và đo đạc các chỉ số W, Wq, L, Lq, rho, Drop rate."),
            ("Bước 3 (Thẩm định):", "So sánh kết quả mô phỏng với nghiệm giải tích chính xác. Đảm bảo toàn bộ sai số tương đối RE <= 5.0%."),
        ]),
    ]

    for pos, sec_title, items in guide_sections:
        ws_guide[pos] = sec_title
        ws_guide[pos].font = font_sec_title
        start_r = int(pos[1:]) + 1
        for offset, (lbl, desc) in enumerate(items):
            cur_r = start_r + offset
            ws_guide[f"A{cur_r}"] = lbl
            ws_guide[f"B{cur_r}"] = desc
            ws_guide[f"A{cur_r}"].font = font_cell_bold
            ws_guide[f"B{cur_r}"].font = font_cell
            ws_guide[f"A{cur_r}"].border = thin_border
            ws_guide[f"B{cur_r}"].border = thin_border
            ws_guide.merge_cells(f"B{cur_r}:G{cur_r}")
            ws_guide[f"B{cur_r}"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            ws_guide.row_dimensions[cur_r].height = 24

    ws_guide.column_dimensions["A"].width = 28
    for c in ["B", "C", "D", "E", "F", "G"]:
        ws_guide.column_dimensions[c].width = 18

    # Import metadata from run_tests_to_excel
    from run_tests_to_excel import TEST_CASES_METADATA, run_analytical_validation_benchmarks

    # ==============================================================================
    # SHEET 2: BẢNG ĐẶC TẢ 31 TEST CASES (INPUT SPECIFICATION)
    # ==============================================================================
    ws_tc = wb.create_sheet(title="🧪 31 Test Cases (Đầu vào)")
    ws_tc.views.sheetView[0].showGridLines = True
    ws_tc.freeze_panes = "A2"

    headers_tc = [
        "STT",
        "Mã Test Case",
        "Phân nhóm chức năng",
        "Tên Hàm Pytest",
        "Thành phần kiểm thử",
        "Mục tiêu kiểm thử",
        "Tiền điều kiện (Preconditions)",
        "Các bước thực hiện (Test Steps)",
        "Dữ liệu & Tham số đầu vào",
        "Kết quả kỳ vọng (Expected Output)",
        "Tiêu chí nghiệm thu (Criteria)",
        "Độ ưu tiên",
    ]

    ws_tc.row_dimensions[1].height = 28
    for col_idx, h in enumerate(headers_tc, start=1):
        cell = ws_tc.cell(row=1, column=col_idx, value=h)
        cell.font = font_th
        cell.fill = PatternFill(start_color=COLOR_PRIMARY, end_color=COLOR_PRIMARY, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = header_border

    test_steps_map = {
        "TC-ASYNC-01": ("Async EventLoop đã khởi tạo", "1. Tạo future với req_id=101\n2. Kiểm tra trạng thái pending\n3. Gọi set_result() với dummy job\n4. await future nhận kết quả", "Critical"),
        "TC-ASYNC-02": ("EventLoop đang chạy", "1. Khởi tạo 3 coroutine tính nhân đôi\n2. Gọi run_with_gather(coros)\n3. Thu nhận mảng kết quả", "High"),
        "TC-ASYNC-03": ("Python 3.11+ TaskGroup sẵn sàng", "1. Khởi tạo 2 coroutine độc lập\n2. Thực thi qua run_with_task_group\n3. Đảm bảo toàn bộ kết thúc an toàn", "High"),
        "TC-ASYNC-04": ("EventLoop đang chạy", "1. Tạo task nhanh (0.01s) và task chậm (0.03s)\n2. Chạy qua process_as_completed\n3. Thu thập kết quả theo thứ tự xong", "Normal"),
        "TC-ASYNC-05": ("Module Runner độc lập", "1. Tạo coroutine đơn lẻ\n2. Gọi AsyncTaskCoordinator.run_in_runner\n3. Kiểm tra dọn sạch loop sau chạy", "Normal"),
        "TC-ASYNC-06": ("SinkLP và FutureManager liên kết", "1. Đăng ký future cho Job 202\n2. Gửi sự kiện DEPARTURE tới SinkLP\n3. SinkLP tự động gọi set_result", "Critical"),
        "TC-ASYNC-07": ("FutureManager rỗng", "1. Tạo future 301, gọi set_exception\n2. Tạo future 401, 402, gọi cancel_all\n3. Bắt đúng ngoại lệ và trạng thái hủy", "Critical"),
        "TC-ASYNC-08": ("FutureManager rỗng", "1. Tạo future 501\n2. Dùng asyncio.wait_for với timeout 0.03s\n3. Chờ hết giờ và bắt TimeoutError", "High"),

        "TC-FRAMEWORK-01": ("Lớp SimulationOptions sẵn sàng", "1. Khởi tạo options với tham số tùy chọn\n2. Gọi to_dict()\n3. Gọi from_dict() và đối chiếu thuộc tính", "Normal"),
        "TC-FRAMEWORK-02": ("Hàm create_event sẵn sàng", "1. Tạo sự kiện với timestamp hợp lệ (t=12.5)\n2. Thử tạo sự kiện với timestamp âm (t=-1)\n3. Bắt lỗi ValueError", "Critical"),
        "TC-FRAMEWORK-03": ("BkSysLogicalProcess khởi tạo", "1. Gọi elapse_virt_time(+5.5)\n2. Thử set lùi thời gian ảo (t=3.0)\n3. Checkpoint trạng thái và khôi phục restore", "Critical"),
        "TC-FRAMEWORK-04": ("Mô hình M/M/1 cấu hình qua Simulation", "1. Cấu hình SimulationOptions Tsim=5000\n2. Gắn 3 trạm Source, Server, Sink vào sim\n3. Gọi sim.run() và đối chiếu lý thuyết", "Critical"),
        "TC-FRAMEWORK-05": ("DistributedEventDispatcher sẵn sàng", "1. Cấu hình dispatcher phân tán từng LP\n2. Đăng ký các trạm LP\n3. Chạy 500s và kiểm tra số sự kiện xử lý", "High"),
        "TC-FRAMEWORK-06": ("BkSysCoLogicalProcess & CoEventLoop", "1. Định nghĩa worker coroutine PDES\n2. Dùng await wait_for và advance_time\n3. Chạy vòng lặp CoEventLoop", "Critical"),
        "TC-FRAMEWORK-07": ("LadderQueue rỗng", "1. Tạo 10.000 sự kiện với timestamp Uniform(0,1000)\n2. Đẩy toàn bộ vào LadderQueue\n3. Rút liên tục và kiểm tra thứ tự không giảm", "Critical"),
        "TC-FRAMEWORK-08": ("BkSysLogicalProcess rỗng", "1. Đăng ký handler cho sự kiện ALERT và CHECKPOINT\n2. Gửi các sự kiện tương ứng qua handle_event\n3. Kiểm tra phân phối đúng hàm", "Normal"),

        "TC-VERIF-01": ("MinHeapPriorityQueue rỗng", "1. Đẩy 7 sự kiện xáo trộn vào hàng đợi\n2. Lần lượt pop toàn bộ sự kiện\n3. Kiểm tra mảng timestamp tăng dần", "Critical"),
        "TC-VERIF-02": ("LadderQueue & MinHeap rỗng", "1. Đẩy cùng dãy 8 sự kiện vào 2 hàng đợi\n2. Lần lượt pop toàn bộ sự kiện ra\n3. So sánh đối chiếu thứ tự hai hàng đợi", "High"),
        "TC-VERIF-03": ("Mô hình QueueServerLP đệm hữu hạn", "1. Chạy mô phỏng 500 đơn vị thời gian\n2. Thu thập arrived, completed, dropped, in_system\n3. Kiểm tra hiệu: Arrived - (Done+Drop+InSys)", "Critical"),
        "TC-VERIF-04": ("Dispatcher hoàn tất chạy 100s", "1. Chạy mô phỏng M/M/1 trong 100s\n2. Trích xuất toàn bộ trace_log\n3. Kiểm tra tính đơn điệu t_i <= t_{i+1}", "Critical"),
        "TC-VERIF-05": ("Dispatcher và trạm M/M/1 sẵn sàng", "1. Cấu hình lambda=6, mu=10, Tsim=5000\n2. Chạy mô phỏng tuần tự\n3. So sánh W và L đo đạc với lý thuyết Little", "Critical"),
        "TC-VERIF-06": ("Hệ thống Erlang loss n=5 server", "1. Cấu hình lambda=8, mu=2, n=5 server\n2. Chạy mô phỏng 5000s\n3. So sánh drop_rate với công thức Erlang-B", "Critical"),
        "TC-VERIF-07": ("Mạng Jackson 4 trạm khởi tạo", "1. Đăng ký 4 trạm IO, CPU, Printer, Disk\n2. Chạy mô phỏng 500s với lambda=2.0\n3. Kiểm tra hoàn thành > 500 jobs không deadlock", "High"),
        "TC-VERIF-08": ("Mạng Jackson hoàn tất chạy 5000s", "1. Chạy mạng 4 trạm trong 5000s\n2. Thu thập trễ từng trạm và trễ toàn trình\n3. Đối chiếu nghiệm giải tích Jackson", "Critical"),
        "TC-VERIF-09": ("Mô hình M/M/1/K đệm K=5", "1. Chạy mô phỏng lambda=8, mu=10, K=5 trong 3000s\n2. Thu thập drop_rate, W, L\n3. So sánh với mm1k_theory", "Critical"),
        "TC-VERIF-10": ("Mô hình M/M/c 3 server", "1. Chạy mô phỏng lambda=15, mu=6, c=3 trong 3000s\n2. Thu thập W, L\n3. So sánh với mmc_theory (Erlang-C)", "Critical"),
        "TC-VERIF-11": ("Mô hình pure delay 100 server", "1. Chạy mô phỏng lambda=10, mu=2, c=100 trong 2000s\n2. Thu thập W, Wq, L\n3. So sánh với mminf_theory", "High"),
        "TC-VERIF-12": ("Mô hình M/M/c/K c=2, K=5", "1. Chạy mô phỏng lambda=14, mu=5, c=2, K=5 trong 3000s\n2. Thu thập drop_rate, W\n3. So sánh với mmck_theory", "Critical"),
        "TC-VERIF-13": ("Mô hình M/M/2/8 có rớt gói", "1. Chạy mô phỏng lambda=12, mu=5, c=2, K=8 trong 2000s\n2. Tính lambda_eff = lambda * (1 - Pb)\n3. Đối chiếu L đo đạc với lambda_eff * W", "Critical"),
        "TC-VERIF-14": ("Dispatcher độc lập", "1. Chạy mô phỏng lần 1 với seed=12345\n2. Chạy mô phỏng lần 2 với cùng seed=12345\n3. So sánh bit-exact kết quả W và độ dài vết", "Critical"),
        "TC-VERIF-15": ("Bộ sinh Uniform(0,1)", "1. Lấy mẫu 50.000 biến ngẫu nhiên theo -ln(1-U)/lambda\n2. Tính kỳ vọng mẫu và phương sai mẫu\n3. So sánh với 1/lambda và 1/lambda^2", "High"),
    }

    for stt, (func_name, meta) in enumerate(TEST_CASES_METADATA.items(), start=1):
        row_idx = stt + 1
        ws_tc.row_dimensions[row_idx].height = 26
        tc_id = meta["id"]
        precond, steps, priority = test_steps_map.get(tc_id, ("Sẵn sàng", "Chạy kiểm thử", "Normal"))

        row_data = [
            stt,
            tc_id,
            meta["category"],
            func_name,
            meta["target"],
            meta["objective"],
            precond,
            steps,
            meta["inputs"],
            meta["expected"],
            meta["tolerance"],
            priority,
        ]

        row_fill = PatternFill(start_color=COLOR_ZEBRA, end_color=COLOR_ZEBRA, fill_type="solid") if (stt % 2 == 0) else None

        for col_idx, val in enumerate(row_data, start=1):
            cell = ws_tc.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_cell
            cell.border = thin_border
            if row_fill:
                cell.fill = row_fill

            if col_idx in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = font_cell_bold
            elif col_idx == 4:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = font_cell_code
            elif col_idx == 12:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if priority == "Critical":
                    cell.fill = PatternFill(start_color=COLOR_CRIT, end_color=COLOR_CRIT, fill_type="solid")
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color="991B1B")
                elif priority == "High":
                    cell.fill = PatternFill(start_color=COLOR_HIGH, end_color=COLOR_HIGH, fill_type="solid")
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color="92400E")
                else:
                    cell.fill = PatternFill(start_color=COLOR_NORM, end_color=COLOR_NORM, fill_type="solid")
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color="1E40AF")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws_tc.auto_filter.ref = f"A1:L{len(TEST_CASES_METADATA) + 1}"

    # Cân chỉnh độ rộng cột Sheet 2
    widths_tc = {
        "A": 6, "B": 16, "C": 26, "D": 36, "E": 28, "F": 44,
        "G": 28, "H": 40, "I": 38, "J": 42, "K": 20, "L": 14
    }
    for col_letter, w in widths_tc.items():
        ws_tc.column_dimensions[col_letter].width = w

    # ==============================================================================
    # SHEET 3: 67 KỊCH BẢN ĐỐI CHUẨN GIẢI TÍCH (INPUT SPECIFICATION)
    # ==============================================================================
    ws_val_in = wb.create_sheet(title="📐 67 Đối chuẩn (Đầu vào)")
    ws_val_in.views.sheetView[0].showGridLines = True
    ws_val_in.freeze_panes = "A2"

    headers_val_in = [
        "STT",
        "Mô hình Hàng đợi (Kendall / Network)",
        "Kịch bản & Mức tải",
        "Tốc độ đến lambda",
        "Tốc độ phục vụ mu",
        "Số máy chủ c",
        "Dung lượng đệm K",
        "Thời gian ảo Tsim",
        "Chỉ số kiểm chứng",
        "Giá trị Lý thuyết Chuẩn (Benchmark)",
        "Đơn vị",
        "Ngưỡng sai số tối đa",
        "Công thức Giải tích áp dụng",
    ]

    ws_val_in.row_dimensions[1].height = 28
    for col_idx, h in enumerate(headers_val_in, start=1):
        cell = ws_val_in.cell(row=1, column=col_idx, value=h)
        cell.font = font_th
        cell.fill = PatternFill(start_color=COLOR_SECONDARY, end_color=COLOR_SECONDARY, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = header_border

    # Lấy 67 kịch bản từ run_analytical_validation_benchmarks
    benchmarks = run_analytical_validation_benchmarks()

    for stt, b in enumerate(benchmarks, start=1):
        row_idx = stt + 1
        ws_val_in.row_dimensions[row_idx].height = 24

        params_str = b["params"]
        lam_val = "-"
        mu_val = "-"
        c_val = "-"
        k_val = "-"
        for p in params_str.split(","):
            p = p.strip()
            if p.startswith("lambda="):
                lam_val = p.split("=")[1].split()[0]
            elif p.startswith("mu="):
                mu_val = p.split("=")[1].split()[0]
            elif p.startswith("c="):
                c_val = p.split("=")[1].split()[0]
            elif p.startswith("K="):
                k_val = p.split("=")[1].split()[0]

        tsim_val = 3000.0 if "2000" not in params_str else 2000.0

        formula_desc = "Định luật Little / Phân phối Markov"
        if "Erlang-B" in b["metric"] or "M/M/n/n" in b["model"]:
            formula_desc = "Công thức đệ quy Erlang-B (Erlang loss)"
        elif "Erlang-C" in b["model"]:
            formula_desc = "Công thức trễ Erlang-C C(c, a)"
        elif "Jackson" in b["model"]:
            formula_desc = "Định lý Jackson (Cân bằng lưu lượng mạng mở)"
        elif "M/M/1/K" in b["model"]:
            formula_desc = "Giải hệ xác suất trạng thái dừng M/M/1/K"
        elif "M/M/c/K" in b["model"]:
            formula_desc = "Phân phối trạng thái dừng đa máy chủ đệm hữu hạn"

        row_data = [
            stt,
            b["model"],
            b.get("scenario", "Tiêu chuẩn"),
            lam_val,
            mu_val,
            c_val,
            k_val,
            tsim_val,
            b["metric"],
            round(b["theory"], 4),
            b["unit"],
            "RE <= 5.0%",
            formula_desc,
        ]

        row_fill = PatternFill(start_color=COLOR_ZEBRA, end_color=COLOR_ZEBRA, fill_type="solid") if (stt % 2 == 0) else None

        for col_idx, val in enumerate(row_data, start=1):
            cell = ws_val_in.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_cell
            cell.border = thin_border
            if row_fill:
                cell.fill = row_fill

            if col_idx in [1, 4, 5, 6, 7, 8, 10, 11, 12]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if col_idx == 10:
                    cell.font = font_cell_bold
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    ws_val_in.auto_filter.ref = f"A1:M{len(benchmarks) + 1}"

    # Cân chỉnh độ rộng cột Sheet 3
    widths_val_in = {
        "A": 6, "B": 36, "C": 30, "D": 14, "E": 14, "F": 12,
        "G": 14, "H": 16, "I": 36, "J": 18, "K": 10, "L": 18, "M": 38
    }
    for col_letter, w in widths_val_in.items():
        ws_val_in.column_dimensions[col_letter].width = w

    # Lưu file ra các đường dẫn đích
    if target_paths is None:
        target_paths = [
            os.path.join(os.path.dirname(__file__), "DanhSach_TestCases_Input.xlsx"),
            os.path.join(os.path.dirname(__file__), "..", "DanhSach_TestCases_Input.xlsx"),
        ]

    for p in target_paths:
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
        wb.save(p)
        print(f"[*] Đã xuất file Excel Đặc tả Test Case (Input): {os.path.abspath(p)}")

    print("🎉 Hoàn tất tạo file DanhSach_TestCases_Input.xlsx!")
    return wb


if __name__ == "__main__":
    generate_input_specification_excel()
