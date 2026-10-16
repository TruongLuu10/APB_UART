"""
Script Python kiểm tra và tương tác UART giữa Laptop PC và Kit FPGA DE2.
Tối giản, ổn định, hỗ trợ:
  [1] Test truyền Bit nhị phân 0/1 & Byte Hex (0x00 - 0xFF)
  [2] Test truyền Ký tự / Chuỗi (Text Echo)
  [3] Xem trạng thái thanh ghi APB
  [4] Đổi cấu hình tự động đồng bộ (8N1, 8E1, 8O1, 7E1, 7O1, 8N2)
"""

import sys
import time
import threading
import serial
import serial.tools.list_ports

def find_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def reader_thread(ser, stop_event):
    """Luồng đọc nền liên tục in dữ liệu từ FPGA về Laptop thời gian thực."""
    while not stop_event.is_set():
        try:
            if ser.in_waiting > 0:
                raw = ser.read(ser.in_waiting)
                # Khi ở chế độ 7-bit, mask bit thứ 8 về 0 để loại bỏ hoàn toàn ký tự lạ
                if ser.bytesize == serial.SEVENBITS:
                    raw = bytes([b & 0x7F for b in raw])
                text = raw.decode('utf-8', errors='replace')
                sys.stdout.write(text)
                sys.stdout.flush()
            else:
                time.sleep(0.01)
        except Exception:
            break

def main():
    print("=" * 60)
    print("   CHUONG TRINH TUONG TAC UART LAPTOP <--> FPGA DE2")
    print("============================================================")

    available_ports = find_serial_ports()
    if not available_ports:
        print("[!] Khong tim thay cong COM nao tren Laptop.")
        return

    default_port = 'COM4' if 'COM4' in available_ports else available_ports[0]
    print(f"Cac cong COM tim thay: {available_ports}")
    port_choice = input(f"Nhap cong COM muon su dung (mac dinh '{default_port}'): ").strip()
    if not port_choice:
        port_choice = default_port

    try:
        ser = serial.Serial(
            port=port_choice,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1
        )
    except Exception as e:
        print(f"[-] Loi khi mo cong {port_choice}: {e}")
        return

    print(f"[+] Da ket noi thanh cong voi {port_choice} (115200 8N1)!")
    print("------------------------------------------------------------")
    print(" HUONG DAN NHANH:")
    print("  * Nhap 1: Phat du lieu chu dong tu FPGA -> Laptop (Burst, Telemetry)")
    print("  * Nhap 2: Test truyen bit 0/1 & Hex (Laptop -> FPGA, test bit 7, Parity)")
    print("  * Nhap 3: Test chuoi ky tu (Text Echo dem dong)")
    print("  * Nhap 4: Xem trang thai thanh ghi APB")
    print("  * Nhap 5: Doi cau hinh (8N1, 8E1, 8O1, 7E1, 7O1, 8N2)")
    print("  * Meo : Go 'cfg 7E1', 'cfg 8E1', 'cfg 8N1'... de doi ca hai ben!")
    print("  * Go 'quit' tren Laptop de thoat.")
    print("------------------------------------------------------------\n")

    # Khởi động luồng đọc nền
    stop_event = threading.Event()
    t = threading.Thread(target=reader_thread, args=(ser, stop_event), daemon=True)
    t.start()

    time.sleep(0.1)
    ser.reset_input_buffer()
    # Yêu cầu in menu 1 lần
    ser.write(b'm')

    cfg_map = {
        '8N1': ('1', serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, "8N1 (8 Data, No Parity, 1 Stop)"),
        '8E1': ('2', serial.EIGHTBITS, serial.PARITY_EVEN, serial.STOPBITS_ONE, "8E1 (8 Data, Even Parity, 1 Stop)"),
        '8O1': ('3', serial.EIGHTBITS, serial.PARITY_ODD, serial.STOPBITS_ONE, "8O1 (8 Data, Odd Parity, 1 Stop)"),
        '7E1': ('4', serial.SEVENBITS, serial.PARITY_EVEN, serial.STOPBITS_ONE, "7E1 (7 Data, Even Parity, 1 Stop)"),
        '7O1': ('5', serial.SEVENBITS, serial.PARITY_ODD, serial.STOPBITS_ONE, "7O1 (7 Data, Odd Parity, 1 Stop)"),
        '8N2': ('6', serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_TWO, "8N2 (8 Data, No Parity, 2 Stop)")
    }
    key_to_mode = {'1': '8N1', '2': '8E1', '3': '8O1', '4': '7E1', '5': '7O1', '6': '8N2'}

    in_cfg_menu = False
    in_binary_mode = False
    in_text_mode = False
    in_fpga_tx_menu = False

    def sync_config(mode_name, sync_fpga=True):
        nonlocal in_cfg_menu, in_binary_mode, in_text_mode, in_fpga_tx_menu
        mode = mode_name.upper()
        if mode not in cfg_map:
            print(f"[!] Khong ro '{mode}'. Ho tro: 8N1, 8E1, 8O1, 7E1, 7O1, 8N2")
            return

        choice_key, bs, par, sb, desc = cfg_map[mode]

        prev_binary = in_binary_mode
        prev_text = in_text_mode

        if sync_fpga:
            # Gửi ESC để thoát mọi chế độ con về Menu chính trước
            ser.write(b'\x1b')
            time.sleep(0.08)
            ser.write(b'\r\n')
            time.sleep(0.08)
            ser.reset_input_buffer()

            # Gửi lệnh vào Menu 5 của FPGA và chọn cấu hình
            ser.write(b'5')
            time.sleep(0.1)
            ser.write(choice_key.encode('ascii'))
            time.sleep(0.1)

        # Chuyển cổng COM Laptop đồng bộ ngay lập tức
        ser.bytesize = bs
        ser.parity = par
        ser.stopbits = sb
        ser.reset_input_buffer()
        print(f"\n[Dong Bo] Laptop va FPGA da chuyen sang: {desc}")
        time.sleep(0.1)

        if prev_binary:
            ser.write(b'2')
            time.sleep(0.05)
            in_binary_mode = True
            in_text_mode = False
            in_cfg_menu = False
            in_fpga_tx_menu = False
        elif prev_text:
            ser.write(b'3')
            time.sleep(0.05)
            in_text_mode = True
            in_binary_mode = False
            in_cfg_menu = False
            in_fpga_tx_menu = False
        else:
            in_cfg_menu = False
            in_binary_mode = False
            in_text_mode = False
            in_fpga_tx_menu = False

    try:
        while True:
            cmd = input().strip()
            if cmd.lower() == 'quit' and not in_text_mode and not in_binary_mode:
                print("\n[+] Dang thoat chuong trinh...")
                break

            if not cmd:
                if in_fpga_tx_menu:
                    ser.write(b"\r\n")
                continue

            if cmd.lower() in ['menu', 'm', 'help']:
                ser.write(b'm')
                in_cfg_menu = False
                in_binary_mode = False
                in_text_mode = False
                in_fpga_tx_menu = False
                continue

            # Lệnh 'cfg <mode>': Đồng bộ cả 2 bên tức thì
            if cmd.lower().startswith('cfg '):
                parts = cmd.split()
                if len(parts) >= 2:
                    sync_config(parts[1], sync_fpga=True)
                continue

            # Nếu đang ở Menu Phát dữ liệu chủ động từ FPGA (Chế độ 1):
            if in_fpga_tx_menu:
                if cmd.lower() in ['q', 'exit']:
                    ser.write(b"q\r\n")
                    in_fpga_tx_menu = False
                    continue
                else:
                    ser.write((cmd + "\r\n").encode('utf-8'))
                    continue

            # Nếu đang ở chế độ Test Bit 0/1 & Hex (Chế độ 2):
            if in_binary_mode:
                if cmd.lower() in ['q', 'exit', 'quit', 'esc']:
                    ser.write(b'\x1b')
                    in_binary_mode = False
                    continue

                val = None
                # Nhập dạng nhị phân 01 (vd: 10101010 hoặc 10101010b)
                clean_bin = cmd.lower().rstrip('b')
                if len(clean_bin) in [7, 8] and all(c in '01' for c in clean_bin):
                    val = int(clean_bin, 2)
                # Nhập dạng Hex (vd: 0xAA, 0xFF, AA)
                elif cmd.lower().startswith('0x'):
                    try: val = int(cmd, 16)
                    except ValueError: pass
                else:
                    try: val = int(cmd, 16)
                    except ValueError: pass

                if val is not None and 0 <= val <= 255:
                    ser.write(bytes([val]))
                    # Tính toán và hiển thị bit Parity mà phần cứng UART Laptop phát đi
                    effective_val = val & (0x7F if ser.bytesize == serial.SEVENBITS else 0xFF)
                    ones = bin(effective_val).count('1')
                    if ser.parity == serial.PARITY_EVEN:
                        p_bit = 1 if (ones % 2 != 0) else 0
                        p_str = f", Parity Bit={p_bit} (Even, Tong 1s={ones+p_bit})"
                    elif ser.parity == serial.PARITY_ODD:
                        p_bit = 1 if (ones % 2 == 0) else 0
                        p_str = f", Parity Bit={p_bit} (Odd, Tong 1s={ones+p_bit})"
                    else:
                        p_str = " (No Parity)"

                    if ser.bytesize == serial.SEVENBITS:
                        print(f" -> [Laptop da gui]: Hex=0x{effective_val:02X}, Bin={effective_val:07b}b (7-bit){p_str}")
                    else:
                        print(f" -> [Laptop da gui]: Hex=0x{val:02X}, Bin={val:08b}b (Bit 7 MSB={val>>7}){p_str}")
                else:
                    print("[!] Vui long nhap chuoi 8-bit (vd: 10101010), ma Hex (vd: 0xAA), hoac 'q' de thoat.")
                continue

            # Nếu đang ở chế độ Test Ký tự / Chuỗi (Chế độ 3):
            if in_text_mode:
                if cmd.lower() in ['q', 'exit', 'quit']:
                    # Gửi chuỗi "q\r\n" để FPGA xác nhận thoát khỏi đệm dòng
                    ser.write(b"q\r\n")
                    in_text_mode = False
                    continue
                else:
                    ser.write((cmd + "\r\n").encode('utf-8'))
                    continue

            # Nếu đang ở Menu đổi cấu hình (phím 1..6):
            if in_cfg_menu:
                if cmd in key_to_mode:
                    target_mode = key_to_mode[cmd]
                    ser.write(cmd.encode('ascii'))
                    time.sleep(0.05)
                    sync_config(target_mode, sync_fpga=False)
                    continue
                elif cmd.lower() in ['q', 'exit']:
                    ser.write(b'q')
                    in_cfg_menu = False
                    continue

            # Điều hướng từ Menu chính:
            if cmd == '1':
                in_fpga_tx_menu = True
                in_binary_mode = False
                in_text_mode = False
                in_cfg_menu = False
                ser.write(b'1')
                continue

            if cmd == '2':
                in_binary_mode = True
                in_fpga_tx_menu = False
                in_text_mode = False
                in_cfg_menu = False
                ser.write(b'2')
                p_name = 'N' if ser.parity == serial.PARITY_NONE else ('E' if ser.parity == serial.PARITY_EVEN else 'O')
                print(f" -> [Che do 2] Laptop COM: {ser.bytesize}{p_name}{1 if ser.stopbits == serial.STOPBITS_ONE else 2}. Go 'exit' hoac 'q' de thoat.")
                continue

            if cmd == '3':
                in_text_mode = True
                in_fpga_tx_menu = False
                in_binary_mode = False
                in_cfg_menu = False
                ser.write(b'3')
                continue

            if cmd == '4':
                ser.write(b'4')
                continue

            if cmd == '5':
                in_cfg_menu = True
                in_fpga_tx_menu = False
                in_binary_mode = False
                in_text_mode = False
                ser.write(b'5')
                continue

            # Gửi lệnh 1 ký tự hoặc chuỗi text mặc định
            if len(cmd) == 1:
                ser.write(cmd.encode('utf-8'))
            else:
                ser.write((cmd + "\r\n").encode('utf-8'))

    except KeyboardInterrupt:
        print("\n[+] Nhan Ctrl+C, dang thoat...")
    finally:
        stop_event.set()
        time.sleep(0.1)
        ser.close()
        print("[+] Da dong cong COM an toan.")

if __name__ == "__main__":
    main()
