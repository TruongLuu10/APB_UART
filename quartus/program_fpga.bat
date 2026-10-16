@echo off
setlocal
echo ========================================================
echo  Nap Bitstream SOF len FPGA DE2-115 qua USB-Blaster
echo ========================================================

set QUARTUS_DIR=D:\Quartus\altera_lite\25.1std
set PATH=%QUARTUS_DIR%\quartus\bin64;%PATH%

set SOF_FILE=%~dp0output_files\apb_uart.sof

if not exist "%SOF_FILE%" (
    echo [-] Khong tim thay file %SOF_FILE%
    pause
    exit /b 1
)

echo [+] Dang quet thiet bi USB-Blaster va nap %SOF_FILE%...
quartus_pgm -m jtag -o "p;%SOF_FILE%"

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  NAP BITSTREAM SOF THANH CONG!
    echo ========================================================
) else (
    echo [-] Co loi khi nap SOF. Vui long kiem tra cong USB-Blaster va nguon bo mach DE2.
)
if "%~1"=="" pause
