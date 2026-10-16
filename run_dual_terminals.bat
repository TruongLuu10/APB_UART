@echo off
chcp 65001 > nul
cls
echo =====================================================================
echo    KHOI DONG HE THONG GIAO TIEP 2 CUA SO TERMINAL (LAPTOP ^<--^> FPGA)
echo =====================================================================
echo.
echo  [1] Cua so ben TRAI : Terminal Laptop (Phat / Thu May Tinh)
echo  [2] Cua so ben PHAI : Terminal FPGA DE2-115 (Vi xu ly Nios V APB UART)
echo.
echo  * Hai cua so se tu dong can chinh chia doi man hinh (Trai - Phai)!
echo =====================================================================
echo.

cd /d "%~dp0"

echo [+] Dang khoi dong Cua so Phai (FPGA Terminal Server)...
start "FPGA DE2-115 SoC Terminal" cmd /k python "%~dp0firmware\dual_terminal\terminal_fpga.py"

timeout /t 2 /nobreak > nul

echo [+] Dang khoi dong Cua so Trai (Laptop Terminal Client)...
start "Laptop Terminal" cmd /k python "%~dp0firmware\dual_terminal\terminal_laptop.py"

echo.
echo [OK] Ca 2 cua so da duoc khoi dong va xep song song thanh cong!
echo Ban co the thu truyen ngay lap tuc!
