@echo off
setlocal
echo ========================================================
echo  Nap Firmware ELF len CPU FPGA DE2 qua USB-Blaster
echo ========================================================

set QUARTUS_DIR=D:\Quartus\altera_lite\25.1std
set PATH=%QUARTUS_DIR%\quartus\bin64;%QUARTUS_DIR%\niosv\bin;%QUARTUS_DIR%\riscfree\debugger\gdbserver-riscv;%QUARTUS_DIR%\riscfree\toolchain\riscv32-unknown-elf\bin;%PATH%

set ELF_FILE=%~dp0app\build\apb_uart.elf

if not exist "%ELF_FILE%" (
    echo [-] Khong tim thay file %ELF_FILE%
    echo     Vui long chay build_firmware.bat truoc!
    pause
    exit /b 1
)

echo [+] Dang nap file: %ELF_FILE%
niosv-download -g -r "%ELF_FILE%"

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  NAP FIRMWARE THANH CONG VA CPU DANG CHAY!
    echo ========================================================
) else (
    echo [-] Co loi xay ra khi nap firmware. Kiem tra cap USB-Blaster va file .sof da nap chua.
)
if "%~1"=="" pause
