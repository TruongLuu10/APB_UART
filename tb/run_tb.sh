#!/bin/bash
# Script chay mo phong testbench cho UART:
#   ./tb/run_tb.sh          -> chay test ca he thong UART (tb_apb_uart.v)
#   ./tb/run_tb.sh inter    -> chay test rieng khoi interface (tb_top_interface_uart_slave.v)

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "=========================================================="
echo "          CHAY MO PHONG HE THONG APB UART"
echo "=========================================================="

MODE="${1:-top}"

if [ "$MODE" == "inter" ] || [ "$MODE" == "interface" ]; then
    echo "[INFO] Dang chay Testbench rieng cho INTERFACE: tb/tb_top_interface_uart_slave.v"
    FILES="rtl/interface_uart/*.v tb/tb_top_interface_uart_slave.v"
else
    echo "[INFO] Dang chay Testbench cho CA HE THONG UART: tb/tb_apb_uart.v"
    FILES="rtl/*.v rtl/*/*.v tb/tb_apb_uart.v"
fi

if command -v iverilog &> /dev/null; then
    echo "[INFO] Bien dich bang Icarus Verilog (iverilog)..."
    iverilog -g2012 -o sim_out $FILES
    echo "[INFO] Ket qua mo phong:"
    echo "----------------------------------------------------------"
    vvp sim_out
    rm -f sim_out
elif [ -x /home/numb/Downloads/altera_lite/25.1std/questa_fse/bin/vlog ]; then
    echo "[INFO] Kiem tra cu phap bang QuestaSim Compiler (vlog):"
    /home/numb/Downloads/altera_lite/25.1std/questa_fse/bin/vlog -work work $FILES
    echo ""
    echo "[NOTE] De chay simulation xem ket qua truc tiep tren terminal, hay cai iverilog:"
    echo "  sudo apt install -y iverilog"
    echo "Sau do chay: ./tb/run_tb.sh"
else
    echo "[ERROR] Chua cai dat trinh bien dich iverilog. Chay: sudo apt install -y iverilog"
fi
