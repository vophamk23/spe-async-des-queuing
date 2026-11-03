@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
title SPE Asynchronous Queuing Simulator (CO3007 - HK261)
if exist "%~dp0simulator" (cd /d "%~dp0simulator") else (cd /d "%~dp0")

:MENU
cls
echo ================================================================================
echo        HE THONG MO PHONG HANG DOI SU KIEN ROI RAC VA ASYNCIO (CO3007)
echo        Nhom SPE-L0x-008 - Dai hoc Bach Khoa TP.HCM (HK261)
echo ================================================================================
echo.
echo   [1] Chay toan bo 31 bai kiem thu tu dong (Verification, Framework ^& Async Tests)
echo   [2] Mo phong M/M/1 (Don server, dem vo han, lambda=8, mu=10)
echo   [3] Mo phong M/M/1/K (Don server, dem huu han K=5, khao sat rot goi)
echo   [4] Mo phong M/M/c (Da server song song c=3, lambda=15, mu=6)
echo   [5] Mo phong M/M/n/n (Erlang loss n=5, kiem dinh cong thuc Erlang-B)
echo   [6] Mo phong Mang hang doi da chang (Queuing Network - Hinh 1 de bai)
echo   [7] Chay toan bo Thuc nghiem khao sat ^& Xuat bieu do (experiments/)
echo   [8] Bien dich Bao cao LaTeX sang PDF (report/main.pdf)
echo   [9] Chay kiem thu ^& Xuat ca 2 file Excel (Dau vao de test ^& Bao cao ket qua)
echo   [0] Thoat
echo.
echo ================================================================================
set /p opt="Nhap lua chon cua ban [0-9]: "

if "%opt%"=="1" goto TEST_ALL
if "%opt%"=="2" goto RUN_MM1
if "%opt%"=="3" goto RUN_MM1K
if "%opt%"=="4" goto RUN_MMC
if "%opt%"=="5" goto RUN_MMNN
if "%opt%"=="6" goto RUN_NETWORK
if "%opt%"=="7" goto RUN_EXPERIMENTS
if "%opt%"=="8" goto BUILD_REPORT
if "%opt%"=="9" goto RUN_EXCEL
if "%opt%"=="0" goto EXIT_PROG
echo.
echo [!] Lua chon khong hop le. Vui long chon tu 0 den 9!
timeout /t 2 > nul
goto MENU

:TEST_ALL
cls
echo ================================================================================
echo [*] DANG CHAY 31 BAI KIEM THU TU DONG (VERIFICATION, FRAMEWORK ^& ASYNC SPEC)...
echo ================================================================================
pytest tests/ -v
echo.
echo ================================================================================
pause
goto MENU

:RUN_MM1
cls
echo ================================================================================
echo [*] CHAY MO PHONG M/M/1: lambda=8.0, mu=10.0, sim_time=5000s
echo ================================================================================
python main.py --model MM1 --lambda 8.0 --mu 10.0 --sim-time 5000 --replications 5
echo.
echo ================================================================================
pause
goto MENU

:RUN_MM1K
cls
echo ================================================================================
echo [*] CHAY MO PHONG M/M/1/K: lambda=10.0, mu=8.0, K=5 (QUA TAI KHAO SAT ROT GOI)
echo ================================================================================
python main.py --model MM1K --lambda 10.0 --mu 8.0 --capacity 5 --sim-time 5000 --replications 5
echo.
echo ================================================================================
pause
goto MENU

:RUN_MMC
cls
echo ================================================================================
echo [*] CHAY MO PHONG M/M/c: c=3 servers, lambda=15.0, mu=6.0 (Erlang-C)
echo ================================================================================
python main.py --model MMC --lambda 15.0 --mu 6.0 --servers 3 --sim-time 5000 --replications 5
echo.
echo ================================================================================
pause
goto MENU

:RUN_MMNN
cls
echo ================================================================================
echo [*] CHAY MO PHONG M/M/n/n (ERLANG LOSS): n=5 servers, lambda=12.0, mu=3.0
echo ================================================================================
python main.py --model MMNN --lambda 12.0 --mu 3.0 --servers 5 --sim-time 5000 --replications 5
echo.
echo ================================================================================
pause
goto MENU

:RUN_NETWORK
cls
echo ================================================================================
echo [*] CHAY MO PHONG MANG HANG DOI DA CHANG (HINH 1 DE BAI - 4 TRAM)
echo ================================================================================
python main.py --model network --lambda 2.0 --sim-time 5000 --replications 5
echo.
echo ================================================================================
pause
goto MENU

:RUN_EXPERIMENTS
cls
echo ================================================================================
echo [*] CHAY TOAN BO 4 KICH BAN THUC NGHIEM ^& XUAT BIEU DO 300 DPI
echo ================================================================================
python experiments/run_all_experiments.py
echo.
echo [*] Da xuat cac bieu do vao thu muc plots/:
echo     - mm1_utilization_sweep.png
echo     - mm1k_buffer_loss.png
echo     - mmc_multiserver_latency.png
echo     - network_bottleneck_analysis.png
echo.
echo ================================================================================
pause
goto MENU

:BUILD_REPORT
cls
echo ================================================================================
echo [*] BIEN DICH BAO CAO LATEX SANG PDF...
echo ================================================================================
cd /d "%~dp0\report"
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
copy /Y main.pdf "..\Spe-Ass-Spec-SPE-L0x-008.pdf" > nul
if exist "%~dp0simulator" (cd /d "%~dp0simulator") else (cd /d "%~dp0")
echo [*] Bien dich hoan tat: File PDF moi da duoc cap nhat tai goc du an!
echo ================================================================================
pause
goto MENU

:RUN_EXCEL
cls
echo ================================================================================
echo [*] DANG CHAY 31 TEST CASES ^& DONG BO HE THONG 2 FILE EXCEL KIEM THU...
echo ================================================================================
python run_tests_to_excel.py
echo.
echo [*] DA XUAT THANH CONG DAY DU 2 BO FILE EXCEL:
echo     1. FILE KICH BAN DAU VAO (DE TEST / EDIT THAM SO):
echo        - DanhSach_TestCases_Input.xlsx
echo     2. FILE BAO CAO KET QUA THUC THI (DASHBOARD ^& THONG KE):
echo        - BaoCao_KetQua_KiemThu.xlsx (Tu dong mo sau khi chay)
echo ================================================================================
pause
goto MENU

:EXIT_PROG
exit /b 0

