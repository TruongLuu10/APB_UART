"""
================================================================================
  CỬA SỔ BÊN TRÁI: TERMINAL LAPTOP (CLIENT TRANSMITTER & RECEIVER)
  - Tự động căn chỉnh sang NỬA TRÁI màn hình Windows
  - Cho phép nhập: Mã Nhị phân (10101010b), Mã Hex (0xAA), Chuỗi ký tự (abc)
  - Hỗ trợ đổi cấu hình 1-chạm: 8e1, 8o1, 8n1, 7e1, 7o1, 8n2
  - QUY TẮC HIỂN THỊ:
    + Khi Laptop phát: Cửa sổ Laptop hiện khung ĐÃ PHÁT; FPGA hiện khung ĐÃ NHẬN
    + Khi FPGA phát: Cửa sổ Laptop hiện khung ĐÃ NHẬN; FPGA KHÔNG hiện lặp lại
================================================================================
"""

import sys
import os
import time
import json
import socket
import threading
import ctypes
from colorama import init, Fore, Back, Style

init(autoreset=True)

TCP_PORT = 9876
current_cfg = "8N1"

cfg_info = {
    '8N1': {'bits': 8, 'parity': 'NONE', 'stop': 1, 'desc': '8 Data, No Parity, 1 Stop'},
    '8E1': {'bits': 8, 'parity': 'EVEN', 'stop': 1, 'desc': '8 Data, Even Parity, 1 Stop'},
    '8O1': {'bits': 8, 'parity': 'ODD',  'stop': 1, 'desc': '8 Data, Odd Parity, 1 Stop'},
    '7E1': {'bits': 7, 'parity': 'EVEN', 'stop': 1, 'desc': '7 Data, Even Parity, 1 Stop'},
    '7O1': {'bits': 7, 'parity': 'ODD',  'stop': 1, 'desc': '7 Data, Odd Parity, 1 Stop'},
    '8N2': {'bits': 8, 'parity': 'NONE', 'stop': 2, 'desc': '8 Data, No Parity, 2 Stop'}
}

# Tự động ghim cửa sổ sang nửa bên trái màn hình
def snap_to_left():
    if os.environ.get("TERM_PROGRAM") == "vscode" or "VSCODE_PID" in os.environ:
        return
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        w = sw // 2
        h = sh - 55
        x = 0
        y = 0
        title = "Laptop Terminal [Tram Phat & Thu May Tinh]"
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
    print(Fore.CYAN + Style.BRIGHT + "=" * 70)
    print(Fore.YELLOW + Style.BRIGHT + "  🖥️   CỬA SỔ TRÁI: TERMINAL LAPTOP (CLIENT TRANSMITTER & RECEIVER)")
    print(Fore.WHITE + f"      Cấu hình UART hiện tại : {current_cfg} ({cfg_info[current_cfg]['desc']})")
    print(Fore.CYAN + Style.BRIGHT + "=" * 70)
    print(Fore.WHITE + " HƯỚNG DẪN TRUYỀN TÍN HIỆU TỪ LAPTOP SANG FPGA:")
    print(Fore.GREEN + "  * Truyền nhị phân 01 : Gõ vd: 10101010b, 10100101b, 0100101b")
    print(Fore.GREEN + "  * Truyền mã Hex      : Gõ vd: 0xAA, 0x55, 0xFF, AA")
    print(Fore.GREEN + "  * Truyền chuỗi Text  : Gõ bất kỳ chữ gì (vd: hello, FPGA DE2)")
    print(Fore.YELLOW + "  * Đổi cấu hình khung : Gõ 8e1, 8o1, 8n1, 7e1, 7o1, 8n2")
    print(Fore.WHITE + "  * Gõ 'help' để xem lại menu | Gõ 'quit' để thoát.")
    print(Fore.CYAN + Style.BRIGHT + "-" * 70 + "\n")

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

def print_laptop_tx_box(details):
    print(Fore.CYAN + Style.BRIGHT + "\n╔══════════════════════════════════════════════════════════════════════╗")
    print(Fore.CYAN + Style.BRIGHT + "║  💻  [LAPTOP ĐÃ PHÁT TÍN HIỆU SANG FPGA]                             ║")
    line1 = f"║  * Dữ liệu         : 0x{details['eff_val']:02X} (Dec: {details['eff_val']}{details['char_repr']})"
    print(Fore.WHITE + line1 + " " * max(1, 71 - len(line1)) + "║")
    line2 = f"║  * Dạng Binary     : {details['bin_str']}"
    print(Fore.WHITE + line2 + " " * max(1, 71 - len(line2)) + "║")
    line3 = f"║  * Bit 7 (MSB)     : {details['msb_str']}"
    print(Fore.WHITE + line3 + " " * max(1, 71 - len(line3)) + "║")
    line4 = f"║  * Cấu hình khung  : {current_cfg} ({cfg_info[current_cfg]['desc']})"
    print(Fore.YELLOW + line4 + " " * max(1, 71 - len(line4)) + "║")
    line5 = f"║  * Parity phát đi  : Bit Parity = {details['p_str']}"
    print(Fore.GREEN + Style.BRIGHT + line5 + " " * max(1, 71 - len(line5)) + "║")
    print(Fore.CYAN + Style.BRIGHT + "╚══════════════════════════════════════════════════════════════════════╝\n")

def print_laptop_tx_str_box(text):
    print(Fore.CYAN + Style.BRIGHT + "\n┌──────────────────────────────────────────────────────────────────────┐")
    print(Fore.CYAN + Style.BRIGHT + "│  💻  [LAPTOP ĐÃ PHÁT CHUỖI VĂN BẢN SANG FPGA]                        │")
    line1 = f"│  * Chuỗi ký tự     : \"{text}\""
    print(Fore.WHITE + line1 + " " * max(1, 71 - len(line1)) + "│")
    line2 = f"│  * Độ dài chuỗi    : {len(text)} byte"
    print(Fore.WHITE + line2 + " " * max(1, 71 - len(line2)) + "│")
    line3 = f"│  * Cấu hình khung  : {current_cfg}"
    print(Fore.YELLOW + line3 + " " * max(1, 71 - len(line3)) + "│")
    print(Fore.CYAN + Style.BRIGHT + "└──────────────────────────────────────────────────────────────────────┘\n")

def print_laptop_rx_box(val, bin_str, msb_str, p_str, is_err):
    char_repr = f", Ký tự: '{chr(val)}'" if (32 <= val <= 126) else ""
    border_color = Fore.RED + Style.BRIGHT if is_err else Fore.GREEN + Style.BRIGHT
    print(border_color + "\n╔══════════════════════════════════════════════════════════════════════╗")
    print(border_color + "║  💻  [LAPTOP ĐÃ NHẬN DỮ LIỆU TỪ FPGA]                                ║")
    line1 = f"║  * Dữ liệu         : 0x{val:02X} (Dec: {val}{char_repr})"
    print(Fore.WHITE + line1 + " " * max(1, 71 - len(line1)) + "║")
    line2 = f"║  * Dạng Binary     : {bin_str}"
    print(Fore.WHITE + line2 + " " * max(1, 71 - len(line2)) + "║")
    line3 = f"║  * Bit 7 (MSB)     : {msb_str}"
    print(Fore.WHITE + line3 + " " * max(1, 71 - len(line3)) + "║")
    line4 = f"║  * Cấu hình khung  : {current_cfg} ({cfg_info[current_cfg]['desc']})"
    print(Fore.YELLOW + line4 + " " * max(1, 71 - len(line4)) + "║")
    line5 = f"║  * Bit Parity nhận : Bit Parity = {p_str}"
    print(Fore.WHITE + line5 + " " * max(1, 71 - len(line5)) + "║")
    if is_err:
        line6 = "║  * Kiểm tra Parity : ❌ CẢNH BÁO: LỖI PARITY!"
        print(Fore.RED + Style.BRIGHT + line6 + " " * max(1, 71 - len(line6)) + "║")
    else:
        line6 = "║  * Kiểm tra Parity : ✅ CHÍNH XÁC (Khung truyền hợp lệ)"
        print(Fore.GREEN + Style.BRIGHT + line6 + " " * max(1, 71 - len(line6)) + "║")
    print(border_color + "╚══════════════════════════════════════════════════════════════════════╝\n")
    sys.stdout.write(Fore.YELLOW + "Laptop_TX> " + Style.RESET_ALL)
    sys.stdout.flush()

def print_laptop_rx_str_box(text, length, is_err):
    border_color = Fore.RED + Style.BRIGHT if is_err else Fore.GREEN + Style.BRIGHT
    print(border_color + "\n┌──────────────────────────────────────────────────────────────────────┐")
    print(border_color + "│  💻  [LAPTOP ĐÃ NHẬN CHUỖI VĂN BẢN TỪ FPGA]                          │")
    line1 = f"│  * Nội dung chuỗi  : \"{text}\""
    print(Fore.WHITE + line1 + " " * max(1, 71 - len(line1)) + "│")
    line2 = f"│  * Độ dài chuỗi    : {length} byte"
    print(Fore.WHITE + line2 + " " * max(1, 71 - len(line2)) + "│")
    line3 = f"│  * Cấu hình khung  : {current_cfg}"
    print(Fore.YELLOW + line3 + " " * max(1, 71 - len(line3)) + "│")
    line4 = "│  * Trạng thái      : ✅ Hoàn tất nhận chuỗi"
    print(Fore.GREEN + Style.BRIGHT + line4 + " " * max(1, 71 - len(line4)) + "│")
    print(border_color + "└──────────────────────────────────────────────────────────────────────┘\n")
    sys.stdout.write(Fore.YELLOW + "Laptop_TX> " + Style.RESET_ALL)
    sys.stdout.flush()

def main():
    global current_cfg
    snap_to_left()
    print_banner()

    print(Fore.YELLOW + "[*] Đang kết nối tới Server FPGA (127.0.0.1:9876)...")
    sock = None
    for attempt in range(25):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', TCP_PORT))
            print(Fore.GREEN + Style.BRIGHT + "[+] ĐÃ KẾT NỐI THÀNH CÔNG VỚI CỬA SỔ FPGA BÊN PHẢI!\n")
            break
        except Exception:
            time.sleep(0.4)

    if not sock:
        print(Fore.RED + "[!] Không thể kết nối tới terminal_fpga.py! Hãy mở cửa sổ FPGA trước.")
        input("Nhấn Enter để thoát...")
        sys.exit(1)

    # Luồng nhận dữ liệu từ FPGA
    def rx_from_fpga_loop():
        global current_cfg
        buf = ""
        while True:
            try:
                data = sock.recv(2048)
                if not data:
                    print(Fore.RED + "\n[!] Kết nối với FPGA đã bị đóng!")
                    break
                buf += data.decode('utf-8', errors='ignore')
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        m_type = msg.get("type")

                        # 1. Đồng bộ cấu hình
                        if m_type in ["CFG_SYNC", "CFG_OK"]:
                            current_cfg = msg.get("mode", "8N1")
                            desc = cfg_info[current_cfg]['desc']
                            print(Fore.CYAN + Style.BRIGHT + "\n" + "═" * 70)
                            print(Fore.CYAN + Style.BRIGHT + f"⚡ [ĐỒNG BỘ CẤU HÌNH THÀNH CÔNG] Cả Laptop & FPGA đã chuyển sang: {current_cfg}")
                            print(Fore.WHITE + f"   Chi tiết khung truyền: {desc}")
                            print(Fore.CYAN + Style.BRIGHT + "═" * 70 + "\n")

                        # 2. Nhận byte từ FPGA phát sang Laptop
                        elif m_type == "FPGA_SENT_BYTE":
                            val = int(msg.get("val", 0))
                            bin_str = msg.get("bin", f"{val:08b}b")
                            msb_str = str(msg.get("msb", (val >> 7) & 1))
                            p_str = msg.get("p_str", "Không rõ")
                            is_err = bool(msg.get("par_err", 0))
                            print_laptop_rx_box(val, bin_str, msb_str, p_str, is_err)

                        # 3. Nhận chuỗi từ FPGA phát sang Laptop
                        elif m_type == "FPGA_SENT_TEXT":
                            text = msg.get("text", "")
                            length = msg.get("len", len(text))
                            is_err = bool(msg.get("par_err", 0))
                            print_laptop_rx_str_box(text, length, is_err)

                    except json.JSONDecodeError:
                        pass
            except Exception:
                break

    t_rx = threading.Thread(target=rx_from_fpga_loop, daemon=True)
    t_rx.start()

    # Vòng lặp nhập lệnh tại Cửa sổ Laptop
    try:
        while True:
            try:
                cmd = input(Fore.YELLOW + "Laptop_TX> " + Style.RESET_ALL).strip()
            except EOFError:
                break

            if not cmd:
                continue

            if cmd.lower() in ['quit', 'exit']:
                print(Fore.YELLOW + "\n[+] Đang thoát Laptop Terminal...")
                break

            if cmd.lower() in ['help', '?']:
                print_banner()
                continue

            kind, val = parse_user_input(cmd)

            if kind == "CFG":
                # Yêu cầu đổi cấu hình
                msg = json.dumps({"action": "SET_CFG", "mode": val}) + "\n"
                sock.sendall(msg.encode('utf-8'))

            elif kind == "BYTE":
                # Tính toán chi tiết phát đi
                details = compute_tx_details(val, current_cfg)
                # In khung ĐÃ PHÁT trên màn hình Laptop
                print_laptop_tx_box(details)

                # Gửi yêu cầu sang Server FPGA để nạp ra chân UART kit DE2
                msg_b = json.dumps({"action": "LAPTOP_TX_BYTE", "val": details['eff_val']}) + "\n"
                sock.sendall(msg_b.encode('utf-8'))

            elif kind == "TEXT":
                print_laptop_tx_str_box(val)

                msg_t = json.dumps({"action": "LAPTOP_TX_TEXT", "text": val}) + "\n"
                sock.sendall(msg_t.encode('utf-8'))

    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        print(Fore.YELLOW + "\n[+] Đã đóng kết nối Laptop Terminal.")

if __name__ == '__main__':
    main()
