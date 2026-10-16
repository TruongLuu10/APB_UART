@echo off
setlocal
echo ========================================================
echo  Bien dich Firmware C cho FPGA DE2 (Nios V APB UART)
echo ========================================================

set QUARTUS_DIR=D:\Quartus\altera_lite\25.1std
set PATH=%QUARTUS_DIR%\riscfree\build_tools\bin;%QUARTUS_DIR%\riscfree\build_tools\cmake\bin;%QUARTUS_DIR%\riscfree\toolchain\riscv32-unknown-elf\bin;%QUARTUS_DIR%\niosv\bin;%PATH%

cd /d "%~dp0app"
if not exist build mkdir build

echo [+] Cau hinh CMake...
cmake -G "Unix Makefiles" -B build
if %errorlevel% neq 0 (
    echo [-] Loi cau hinh CMake!
    exit /b %errorlevel%
)

echo [+] Tien hanh bien dich ELF va HEX...
make -C build
if %errorlevel% neq 0 (
    echo [-] Loi bien dich!
    exit /b %errorlevel%
)

echo.
echo [+] Cap nhat Firmware HEX vao RAM cua FPGA Bitstream (.sof)...
copy /y "%~dp0app\build\on_chip_mem.hex" "%~dp0..\quartus\system_on_chip_mem.hex" >nul
copy /y "%~dp0app\build\on_chip_mem.hex" "%~dp0..\quartus\system\synthesis\submodules\system_on_chip_mem.hex" >nul

set PATH=%QUARTUS_DIR%\quartus\bin64;%PATH%
pushd "%~dp0..\quartus"
quartus_cdb --update_mif apb_uart
if %errorlevel% neq 0 (
    echo [-] Loi quartus_cdb --update_mif!
    popd
    exit /b %errorlevel%
)
quartus_asm apb_uart
if %errorlevel% neq 0 (
    echo [-] Loi quartus_asm!
    popd
    exit /b %errorlevel%
)
popd

echo.
echo ========================================================
echo  BIEN DICH THANH CONG!
echo  Firmware C da duoc nhung truc tiep vao file:
echo  quartus\output_files\apb_uart.sof
echo.
echo  Ban chi can chay 'program_fpga.bat' de nap ca Phan cung + Code C!
echo ========================================================
if "%~1"=="" pause
