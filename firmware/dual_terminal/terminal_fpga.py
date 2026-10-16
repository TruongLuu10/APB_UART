"""
================================================================================
  CỬA SỔ BÊN PHẢI: TERMINAL FPGA DE2-115 (NIOS V CPU & APB UART)
  - Kết nối trực tiếp với bo mạch kit FPGA DE2-115 qua USB-UART (115200 bps)
  - Đồng bộ khung truyền 8N1, 8E1, 8O1, 7E1, 7O1, 8N2 chuẩn xác tuyệt đối
  - Phân tích trực quan: Giá trị Hex, Dec, Dạng Binary, Bit 7 (MSB), Bit Parity
  - QUY TẮC HIỂN THỊ:
    + Khi FPGA phát: Cửa sổ FPGA hiện khung ĐÃ PHÁT; Laptop hiện khung ĐÃ NHẬN
    + Khi Laptop phát: Cửa sổ FPGA hiện khung ĐÃ NHẬN; Laptop KHÔNG hiện lặp lại
================================================================================
"""

import sys
import os
import time
import json
import socket
import threading
import serial
import serial.tools.list_ports
import ctypes
from colorama import init, Fore, Back, Style

init(autoreset=True)

TCP_PORT = 9876
active_laptop_conn = None
cfg_current = "8N1"
ser = None

cfg_info = {
    '8N1': {'bits': 8, 'ser_bits': serial.EIGHTBITS, 'parity': 'NONE', 'ser_par': serial.PARITY_NONE, 'stop': 1, 'ser_stop': serial.STOPBITS_ONE, 'desc': '8 Data, No Parity, 1 Stop'},
    '8E1': {'bits': 8, 'ser_bits': serial.EIGHTBITS, 'parity': 'EVEN', 'ser_par': serial.PARITY_EVEN, 'stop': 1, 'ser_stop': serial.STOPBITS_ONE, 'desc': '8 Data, Even Parity, 1 Stop'},
    '8O1': {'bits': 8, 'ser_bits': serial.EIGHTBITS, 'parity': 'ODD',  'ser_par': serial.PARITY_ODD,  'stop': 1, 'ser_stop': serial.STOPBITS_ONE, 'desc': '8 Data, Odd Parity, 1 Stop'},
    '7E1': {'bits': 7, 'ser_bits': serial.SEVENBITS, 'parity': 'EVEN', 'ser_par': serial.PARITY_EVEN, 'stop': 1, 'ser_stop': serial.STOPBITS_ONE, 'desc': '7 Data, Even Parity, 1 Stop'},
    '7O1': {'bits': 7, 'ser_bits': serial.SEVENBITS, 'parity': 'ODD',  'ser_par': serial.PARITY_ODD,  'stop': 1, 'ser_stop': serial.STOPBITS_ONE, 'desc': '7 Data, Odd Parity, 1 Stop'},
    '8N2': {'bits': 8, 'ser_bits': serial.EIGHTBITS, 'parity': 'NONE', 'ser_par': serial.PARITY_NONE, 'stop': 2, 'ser_stop': serial.STOPBITS_TWO, 'desc': '8 Data, No Parity, 2 Stop'}
}

# Tự động ghim cửa sổ sang nửa bên phải màn hình
def snap_to_right():
    if os.environ.get("TERM_PROGRAM") == "vscode" or "VSCODE_PID" in os.environ:
        return
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        w = sw // 2
        h = sh - 55
        x = sw // 2
        y = 0
        title = "FPGA DE2-115 SoC Terminal [Phan Cung Nios V]"
        kernel32.SetConsoleTitleW(title)
        time.sleep(0.1)
        hwnd = kernel32.GetConsoleWindow()
        if not hwnd:
            hwnd = user32.FindWindowW(None, title)
        if hwnd:
            user32.MoveWindow(hwnd, x, y, w, h, True)
    except Exception:
        pass

def print_banner():
    print(Fore.GREEN + Style.BRIGHT + "=" * 70)
    print(Fore.YELLOW + Style.BRIGHT + "  ⚡  CỬA SỔ PHẢI: TERMINAL FPGA DE2-115 (NIOS V CPU & APB UART)")
    print(Fore.CYAN + f"     Kit Altera Cyclone IV E | APB UART Base: 0x00022000 @ 50MHz")
    print(Fore.WHITE + f"     Cấu hình UART hiện tại : {cfg_current} ({cfg_info[cfg_current]['desc']})")
    print(Fore.GREEN + Style.BRIGHT + "=" * 70)
    print(Fore.WHITE + " HƯỚNG DẪN TRUYỀN TÍN HIỆU TỪ FPGA SANG LAPTOP:")
    print(Fore.GREEN + "  * Truyền nhị phân 01 : Gõ vd: 10101010b, 10100101b, 0100101b")
    print(Fore.GREEN + "  * Truyền mã Hex      : Gõ vd: 0xAA, 0x55, 0xFF, AA")
    print(Fore.GREEN + "  * Truyền chuỗi Text  : Gõ bất kỳ chữ gì (vd: FPGA OK, Hello DE2)")
    print(Fore.YELLOW + "  * Đổi cấu hình khung : Gõ 8e1, 8o1, 8n1, 7e1, 7o1, 8n2")
    print(Fore.WHITE + "  * Gõ 'help' để xem lại menu | Gõ 'quit' để thoát.")
    print(Fore.GREEN + Style.BRIGHT + "-" * 70 + "\n")

def find_best_com_port():
    all_ports = list(serial.tools.list_ports.comports())
    usb_ports = []
    for p in all_ports:
        desc = f"{p.device} {p.description} {p.hwid}".upper()
        if any(k in desc for k in ["USB", "CP210", "CH340", "FTDI", "UART", "SERIAL"]):
            usb_ports.append(p.device)
    if usb_ports:
        return usb_ports[0], [p.device for p in all_ports]
    elif all_ports:
        return all_ports[0].device, [p.device for p in all_ports]
    return None, []

def compute_tx_details(val, cfg_name):
    cfg = cfg_info.get(cfg_name, cfg_info['8N1'])
    data_bits = cfg['bits']
    parity_mode = cfg['parity']

    effective_val = val & (0x7F if data_bits == 7 else 0xFF)
    ones = bin(effective_val).count('1')

    if data_bits == 7:
        bin_str = f"{effective_val:07b}b (7-bit)"
        msb_str = "DA BI CAT (Khung 7-bit)"
    else:
        bin_str = f"{effective_val:08b}b (8-bit)"
        msb_str = str((effective_val >> 7) & 1)

    if parity_mode == 'EVEN':
        p_bit = 1 if (ones % 2 != 0) else 0
        total_ones = ones + p_bit
        p_str = f"{p_bit} (EVEN, Tổng số bit 1 cả khung = {total_ones} -> Chẵn)"
    elif parity_mode == 'ODD':
        p_bit = 1 if (ones % 2 == 0) else 0
        total_ones = ones + p_bit
        p_str = f"{p_bit} (ODD, Tổng số bit 1 cả khung = {total_ones} -> Lẻ)"
    else:
        p_bit = None
        p_str = "Không sử dụng Parity (NONE)"

    char_repr = f", Ký tự: '{chr(effective_val)}'" if (32 <= effective_val <= 126) else ""
    return {
        "eff_val": effective_val,
        "data_bits": data_bits,
        "bin_str": bin_str,
        "msb_str": msb_str,
        "p_bit": p_bit,
        "p_str": p_str,
        "parity_mode": parity_mode,
        "char_repr": char_repr,
        "ones": ones
    }

def apply_config_safe(mode):
    global cfg_current, active_laptop_conn, ser
    mode = mode.upper().strip()
    if mode.startswith("CFG "):
        mode = mode[4:].strip()
    if mode not in cfg_info:
        print(Fore.RED + f"[!] Không nhận dạng được cấu hình '{mode}'. Hỗ trợ: 8N1, 8E1, 8O1, 7E1, 7O1, 8N2")
        return False

    info = cfg_info[mode]

    # Gửi lệnh chuyển cấu hình sang phần cứng FPGA Nios V qua UART
    try:
        cmd_str = f"!CFG:{mode}\r\n"
        ser.write(cmd_str.encode('ascii'))
        ser.flush()
        time.sleep(0.12)
    except Exception:
        pass

    # Đổi cấu hình cổng COM phía PC
    try:
        ser.bytesize = info['ser_bits']
        ser.parity = info['ser_par']
        ser.stopbits = info['ser_stop']
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception as e:
        print(Fore.RED + f"[!] Lỗi khi đổi cấu hình Serial COM: {e}")
        return False

    cfg_current = mode
    desc = info['desc']

    print(Fore.CYAN + Style.BRIGHT + "\n" + "═" * 70)
    print(Fore.CYAN + Style.BRIGHT + f"⚡ [ĐỒNG BỘ CẤU HÌNH THÀNH CÔNG] Cả FPGA & Laptop đã chuyển sang: {mode}")
    print(Fore.WHITE + f"   Chi tiết khung truyền: {desc}")
    print(Fore.CYAN + Style.BRIGHT + "═" * 70 + "\n")
    sys.stdout.write(Fore.GREEN + "FPGA_TX> " + Style.RESET_ALL)
    sys.stdout.flush()

    # Thông báo cho Cửa sổ Laptop qua TCP
    if active_laptop_conn:
        try:
            msg = json.dumps({"type": "CFG_OK", "mode": mode, "desc": desc}) + "\n"
            active_laptop_conn.sendall(msg.encode('utf-8'))
        except Exception:
            pass
    return True

def parse_user_input(cmd):
    clean = cmd.strip()
    if not clean:
        return None, None

    # 1. Kiểm tra lệnh đổi cấu hình (vd: 8e1, cfg 8e1)
    chk_cfg = clean.upper()
    if chk_cfg.startswith("CFG "):
        chk_cfg = chk_cfg[4:].strip()
    if chk_cfg in cfg_info:
        return "CFG", chk_cfg

    # 2. Kiểm tra nhị phân (vd: 10101010b, 0b10101010, 10101010)
    clean_bin = clean.lower().rstrip('b')
    if clean_bin.startswith('0b'):
        clean_bin = clean_bin[2:]
    if 1 <= len(clean_bin) <= 8 and all(c in '01' for c in clean_bin):
        if clean.lower().endswith('b') or clean.lower().startswith('0b') or len(clean_bin) in [7, 8]:
            try:
                val = int(clean_bin, 2)
                return "BYTE", val
            except ValueError:
                pass

    # 3. Kiểm tra Hex (vd: 0xAA, 0xFF, AA)
    if clean.lower().startswith('0x'):
        try:
            val = int(clean, 16)
            if 0 <= val <= 255:
                return "BYTE", val
        except ValueError:
            pass
    elif len(clean) == 2 and all(c in '0123456789abcdefABCDEF' for c in clean):
        try:
            val = int(clean, 16)
            if 0 <= val <= 255:
                return "BYTE", val
        except ValueError:
            pass

    # 4. Mặc định là chuỗi Text
    return "TEXT", clean

def print_fpga_tx_box(details):
    print(Fore.YELLOW + Style.BRIGHT + "\n╔══════════════════════════════════════════════════════════════════════╗")
    print(Fore.YELLOW + Style.BRIGHT + "║  ⚡  [FPGA ĐÃ PHÁT TÍN HIỆU SANG LAPTOP]                             ║")
    line1 = f"║  * Dữ liệu         : 0x{details['eff_val']:02X} (Dec: {details['eff_val']}{details['char_repr']})"
    print(Fore.WHITE + line1 + " " * max(1, 71 - len(line1)) + "║")
    line2 = f"║  * Dạng Binary     : {details['bin_str']}"
    print(Fore.WHITE + line2 + " " * max(1, 71 - len(line2)) + "║")
    line3 = f"║  * Bit 7 (MSB)     : {details['msb_str']}"
    print(Fore.WHITE + line3 + " " * max(1, 71 - len(line3)) + "║")
    line4 = f"║  * Cấu hình khung  : {cfg_current} ({cfg_info[cfg_current]['desc']})"
    print(Fore.CYAN + line4 + " " * max(1, 71 - len(line4)) + "║")
    line5 = f"║  * Parity phát đi  : Bit Parity = {details['p_str']}"
    print(Fore.GREEN + Style.BRIGHT + line5 + " " * max(1, 71 - len(line5)) + "║")
    print(Fore.YELLOW + Style.BRIGHT + "╚══════════════════════════════════════════════════════════════════════╝\n")

def print_fpga_tx_str_box(text):
    print(Fore.YELLOW + Style.BRIGHT + "\n┌──────────────────────────────────────────────────────────────────────┐")
    print(Fore.YELLOW + Style.BRIGHT + "│  ⚡  [FPGA ĐÃ PHÁT CHUỖI VĂN BẢN SANG LAPTOP]                        │")
    line1 = f"│  * Chuỗi ký tự     : \"{text}\""
    print(Fore.WHITE + line1 + " " * max(1, 71 - len(line1)) + "│")
    line2 = f"│  * Độ dài chuỗi    : {len(text)} byte"
    print(Fore.WHITE + line2 + " " * max(1, 71 - len(line2)) + "│")
    line3 = f"│  * Cấu hình khung  : {cfg_current}"
    print(Fore.CYAN + line3 + " " * max(1, 71 - len(line3)) + "│")
    print(Fore.YELLOW + Style.BRIGHT + "└──────────────────────────────────────────────────────────────────────┘\n")

def print_fpga_rx_box(hex_str, bin_str, bits_str, msb_str, par_mode, par_bit, par_err):
    val = int(hex_str, 16)
    char_repr = f", Ký tự: '{chr(val)}'" if (32 <= val <= 126) else ""
    is_err = (par_err == '1')

    border_color = Fore.RED + Style.BRIGHT if is_err else Fore.GREEN + Style.BRIGHT
    print(border_color + "\n╔══════════════════════════════════════════════════════════════════════╗")
    print(border_color + "║  ⚡  [FPGA ĐÃ NHẬN DỮ LIỆU TỪ LAPTOP]                                ║")
    line1 = f"║  * Dữ liệu         : 0x{hex_str} (Dec: {val}{char_repr})"
    print(Fore.WHITE + line1 + " " * max(1, 71 - len(line1)) + "║")
    line2 = f"║  * Dạng Binary     : {bin_str}b ({bits_str}-bit)"
    print(Fore.WHITE + line2 + " " * max(1, 71 - len(line2)) + "║")
    line3 = f"║  * Bit 7 (MSB)     : {msb_str}"
    print(Fore.WHITE + line3 + " " * max(1, 71 - len(line3)) + "║")
    line4 = f"║  * Cấu hình khung  : {cfg_current} ({cfg_info[cfg_current]['desc']})"
    print(Fore.CYAN + line4 + " " * max(1, 71 - len(line4)) + "║")

    if par_mode == "NONE":
        line5 = "║  * Bit Parity nhận : Không sử dụng (NONE)"
    else:
        ones = bin_str.count('1')
        p_val = 1 if par_bit == '1' else 0
        total = ones + p_val
        p_type_vn = "Chẵn" if par_mode == "EVEN" else "Lẻ"
        line5 = f"║  * Bit Parity nhận : {par_bit} (Tổng số bit 1 cả khung = {total} -> {p_type_vn})"
    print(Fore.WHITE + line5 + " " * max(1, 71 - len(line5)) + "║")

    if is_err:
        line6 = "║  * Kiểm tra Parity : ❌ CẢNH BÁO: PHÁT HIỆN LỖI PARITY (PAR_ERR = 1)!"
        print(Fore.RED + Style.BRIGHT + line6 + " " * max(1, 71 - len(line6)) + "║")
    else:
        line6 = "║  * Kiểm tra Parity : ✅ CHÍNH XÁC (PAR_ERR = 0, Không có lỗi)"
        print(Fore.GREEN + Style.BRIGHT + line6 + " " * max(1, 71 - len(line6)) + "║")
    print(border_color + "╚══════════════════════════════════════════════════════════════════════╝\n")
    sys.stdout.write(Fore.GREEN + "FPGA_TX> " + Style.RESET_ALL)
    sys.stdout.flush()

def print_fpga_rx_str_box(text, length, par_err):
    is_err = (par_err == '1')
    border_color = Fore.RED + Style.BRIGHT if is_err else Fore.GREEN + Style.BRIGHT
    print(border_color + "\n┌──────────────────────────────────────────────────────────────────────┐")
    print(border_color + "│  ⚡  [FPGA ĐÃ NHẬN CHUỖI VĂN BẢN TỪ LAPTOP]                          │")
    line1 = f"│  * Nội dung chuỗi  : \"{text}\""
    print(Fore.WHITE + line1 + " " * max(1, 71 - len(line1)) + "│")
    line2 = f"│  * Độ dài chuỗi    : {length} byte"
    print(Fore.WHITE + line2 + " " * max(1, 71 - len(line2)) + "│")
    line3 = f"│  * Cấu hình khung  : {cfg_current}"
    print(Fore.CYAN + line3 + " " * max(1, 71 - len(line3)) + "│")
    if is_err:
        line4 = "│  * Kiểm tra Parity : ❌ CẢNH BÁO: CÓ BYTE BỊ LỖI PARITY!"
        print(Fore.RED + Style.BRIGHT + line4 + " " * max(1, 71 - len(line4)) + "│")
    else:
        line4 = "│  * Kiểm tra Parity : ✅ CHÍNH XÁC (Không có lỗi Parity)"
        print(Fore.GREEN + Style.BRIGHT + line4 + " " * max(1, 71 - len(line4)) + "│")
    print(border_color + "└──────────────────────────────────────────────────────────────────────┘\n")
    sys.stdout.write(Fore.GREEN + "FPGA_TX> " + Style.RESET_ALL)
    sys.stdout.flush()

def handle_laptop_request(req):
    global ser, cfg_current
    action = req.get("action")

    if action == "LAPTOP_TX_BYTE":
        val = int(req.get("val", 0))
        # Gửi byte dữ liệu thô sang FPGA qua cổng COM và flush tức thì
        ser.write(bytes([val]))
        ser.flush()

    elif action == "LAPTOP_TX_TEXT":
        text = req.get("text", "")
        # Gửi chuỗi text sang FPGA qua cổng COM và flush tức thì
        ser.write((text + "\r\n").encode('utf-8'))
        ser.flush()

    elif action == "SET_CFG":
        mode = req.get("mode", "8N1")
        apply_config_safe(mode)

def main():
    global active_laptop_conn, cfg_current, ser
    snap_to_right()
    print_banner()

    best_port, all_ports = find_best_com_port()
    if not best_port:
        print(Fore.RED + "[!] KHÔNG TÌM THẤY CỔNG COM NÀO!")
        print(Fore.YELLOW + " -> Hãy kiểm tra dây cáp USB-UART nối giữa Laptop và kit DE2-115.")
        input("Nhấn Enter để thoát...")
        sys.exit(1)

    print(Fore.YELLOW + f"Các cổng COM tìm thấy: {all_ports}")
    port_choice = input(f"Chọn cổng COM muốn kết nối (Mặc định '{best_port}'): ").strip()
    if not port_choice:
        port_choice = best_port

    try:
        ser = serial.Serial(
            port=port_choice,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.05
        )
        print(Fore.GREEN + Style.BRIGHT + f"[+] ĐÃ KẾT NỐI THÀNH CÔNG VỚI {port_choice} (115200, 8N1)!\n")
    except Exception as e:
        print(Fore.RED + f"[!] Không thể mở cổng {port_choice}: {e}")
        print(Fore.YELLOW + " -> Lưu ý: Hãy đóng các cửa sổ terminal cũ hoặc PuTTY đang giữ cổng COM này.")
        input("Nhấn Enter để thoát...")
        sys.exit(1)

    # Đưa FPGA về trạng thái sẵn sàng
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.write(b"!CFG:8N1\r\n")
    ser.flush()
    time.sleep(0.05)

    # Khởi động Socket Server nhận kết nối từ Cửa sổ Laptop
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('127.0.0.1', TCP_PORT))
    server_sock.listen(1)

    print(Fore.CYAN + f"[*] IPC Server sẵn sàng tại 127.0.0.1:{TCP_PORT}. Đang chờ Cửa sổ Laptop kết nối...")

    def accept_laptop():
        global active_laptop_conn
        while True:
            try:
                conn, _ = server_sock.accept()
                active_laptop_conn = conn
                print(Fore.MAGENTA + Style.BRIGHT + "\n[+] CỬA SỔ LAPTOP ĐÃ KẾT NỐI VÀ ĐỒNG BỘ THỜI GIAN THỰC!\n")
                sys.stdout.write(Fore.GREEN + "FPGA_TX> " + Style.RESET_ALL)
                sys.stdout.flush()
                msg = json.dumps({"type": "CFG_SYNC", "mode": cfg_current}) + "\n"
                conn.sendall(msg.encode('utf-8'))
            except Exception:
                break

    t_acc = threading.Thread(target=accept_laptop, daemon=True)
    t_acc.start()

    # Luồng nhận yêu cầu từ Cửa sổ Laptop
    def laptop_rx_loop():
        global active_laptop_conn
        buf = ""
        while True:
            if not active_laptop_conn:
                time.sleep(0.1)
                continue
            try:
                data = active_laptop_conn.recv(2048)
                if not data:
                    active_laptop_conn = None
                    continue
                buf += data.decode('utf-8', errors='ignore')
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        req = json.loads(line)
                        handle_laptop_request(req)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                active_laptop_conn = None
                time.sleep(0.1)

    t_lap = threading.Thread(target=laptop_rx_loop, daemon=True)
    t_lap.start()

    # Luồng đọc UART từ phần cứng FPGA (Bắt buộc không bị chặn bởi prefix rác)
    def fpga_uart_read_loop():
        line_buf = ""
        while True:
            try:
                if ser and ser.is_open and ser.in_waiting > 0:
                    raw = ser.read(ser.in_waiting)
                    line_buf += raw.decode('latin-1', errors='ignore')

                    # Nếu có '!', loại bỏ sạch mọi byte rác hoặc echo đứng trước dấu '!' đầu tiên
                    first_excl = line_buf.find('!')
                    if first_excl > 0:
                        line_buf = line_buf[first_excl:]
                    elif first_excl == -1 and len(line_buf) > 100:
                        line_buf = ""

                    while '\n' in line_buf:
                        line, line_buf = line_buf.split('\n', 1)
                        line = line.strip().strip('\r')
                        if not line:
                            continue

                        # 1. Bắt gói tin !RX_BYTE từ phần cứng FPGA khi Laptop phát sang
                        if "!RX_BYTE:" in line:
                            tag_idx = line.find("!RX_BYTE:")
                            content = line[tag_idx + len("!RX_BYTE:"):].strip()
                            fields = {}
                            for item in content.split(','):
                                if '=' in item:
                                    k, v = item.split('=', 1)
                                    fields[k.strip()] = v.strip()

                            hex_str = fields.get("HEX", "00")
                            bin_str = fields.get("BIN", "00000000")
                            bits_str = fields.get("BITS", "8")
                            msb_str = fields.get("MSB", "-")
                            par_mode = fields.get("PAR_MODE", "NONE")
                            par_bit = fields.get("PAR_BIT", "0")
                            par_err = fields.get("PAR_ERR", "0")

                            print_fpga_rx_box(hex_str, bin_str, bits_str, msb_str, par_mode, par_bit, par_err)

                        # 2. Bắt gói tin !RX_STR khi Laptop phát chuỗi
                        elif "!RX_STR:" in line:
                            tag_idx = line.find("!RX_STR:")
                            content = line[tag_idx + len("!RX_STR:"):].strip()
                            fields = {}
                            for item in content.split(','):
                                if '=' in item:
                                    k, v = item.split('=', 1)
                                    fields[k.strip()] = v.strip()
                            text = fields.get("TEXT", "")
                            length = fields.get("LEN", str(len(text)))
                            par_err = fields.get("PAR_ERR", "0")

                            print_fpga_rx_str_box(text, length, par_err)

                        # 3. Lệnh phản hồi !CFG_OK hoặc !READY
                        elif "!CFG_OK:" in line or "!READY:" in line:
                            pass
                else:
                    time.sleep(0.01)
            except Exception:
                time.sleep(0.05)

    t_uart = threading.Thread(target=fpga_uart_read_loop, daemon=True)
    t_uart.start()

    # Vòng lặp nhập lệnh trực tiếp tại Cửa sổ FPGA
    try:
        while True:
            try:
                cmd = input(Fore.GREEN + "FPGA_TX> " + Style.RESET_ALL).strip()
            except EOFError:
                break

            if not cmd:
                continue

            if cmd.lower() in ['quit', 'exit']:
                print(Fore.YELLOW + "\n[+] Đang thoát FPGA Terminal...")
                break

            if cmd.lower() in ['help', '?']:
                print_banner()
                continue

            # Phân tích lệnh người dùng gõ
            kind, val = parse_user_input(cmd)

            if kind == "CFG":
                apply_config_safe(val)

            elif kind == "BYTE":
                # Tính toán chi tiết phát đi
                details = compute_tx_details(val, cfg_current)
                # In khung ĐÃ PHÁT trên màn hình FPGA
                print_fpga_tx_box(details)

                # Ra lệnh cho CPU Nios V phát byte ra cổng UART phần cứng
                hex_tx = f"{details['eff_val']:02X}"
                ser.write(f"!TX_BYTE:{hex_tx}\r\n".encode('ascii'))
                ser.flush()

                # Chuyển tiếp sự kiện sang Laptop qua TCP để Laptop hiện khung ĐÃ NHẬN
                if active_laptop_conn:
                    try:
                        evt = {
                            "type": "FPGA_SENT_BYTE",
                            "val": details['eff_val'],
                            "bin": details['bin_str'],
                            "bits": details['data_bits'],
                            "msb": details['msb_str'],
                            "parity_mode": details['parity_mode'],
                            "parity_bit": details['p_bit'],
                            "p_str": details['p_str'],
                            "char": chr(details['eff_val']) if (32 <= details['eff_val'] <= 126) else ""
                        }
                        active_laptop_conn.sendall((json.dumps(evt) + "\n").encode('utf-8'))
                    except Exception:
                        pass

            elif kind == "TEXT":
                print_fpga_tx_str_box(val)

                # Ra lệnh cho CPU Nios V phát chuỗi ra cổng UART phần cứng
                ser.write(f"!TX_STR:{val}\r\n".encode('utf-8'))
                ser.flush()

                # Chuyển tiếp sự kiện sang Laptop qua TCP để Laptop hiện khung ĐÃ NHẬN
                if active_laptop_conn:
                    try:
                        evt = {
                            "type": "FPGA_SENT_TEXT",
                            "text": val,
                            "len": len(val),
                            "par_err": 0
                        }
                        active_laptop_conn.sendall((json.dumps(evt) + "\n").encode('utf-8'))
                    except Exception:
                        pass

    except KeyboardInterrupt:
        pass
    finally:
        if ser:
            ser.close()
        server_sock.close()
        print(Fore.YELLOW + "\n[+] Đã đóng cổng COM và hoàn tất phiên làm việc.")

if __name__ == '__main__':
    main()
