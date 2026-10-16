@echo off
chcp 65001 > nul
cls
echo =====================================================================
echo    KHOI DONG HE THONG GIAO TIEP 2 CUA SO TERMINAL (LAPTOP ^<--^> FPGA)
echo =====================================================================
echo.
cd /d "%~dp0"

echo [+] Dang khoi dong Cua so Phai (FPGA Terminal Server)...
start "FPGA DE2-115 SoC Terminal" cmd /k python "%~dp0terminal_fpga.py"

timeout /t 2 /nobreak > nul

echo [+] Dang khoi dong Cua so Trai (Laptop Terminal Client)...
start "Laptop Terminal" cmd /k python "%~dp0terminal_laptop.py"

echo.
echo [OK] Ca 2 cua so da duoc khoi dong va xep song song thanh cong!
