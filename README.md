# HỆ THỐNG APB UART TRÊN KIT FPGA ALTERA DE2-115

Dự án thiết kế và hiện thực hóa hệ thống giao tiếp nối tiếp **APB UART (Advanced Peripheral Bus UART)** trên vi mạch FPGA Altera/Intel Cyclone IV E (**EP4CE115F29C7**) thuộc kit phát triển **Terasic DE2-115**, tích hợp cùng vi xử lý 32-bit RISC-V **Nios V/m** và giao tiếp hai chiều với máy tính Laptop PC qua bộ chuyển đổi USB-UART.

---

## 📑 MỤC LỤC
1. [Kiến Trúc Tổng Thể Hệ Thống](#1-kiến-trúc-tổng-thể-hệ-thống)
2. [Bản Đồ Thanh Ghi APB (Memory Map & Registers)](#2-bản-đồ-thanh-ghi-apb-memory-map--registers)
3. [Cấu Trúc Thư Mục Dự Án](#3-cấu-trúc-thư-mục-dự-án)
4. [Sơ Đồ Kết Nối Phần Cứng (Hardware Pinout)](#4-sơ-đồ-kết-nối-phần-cứng-hardware-pinout)
5. [Hướng Dẫn Biên Dịch & Nạp Hệ Thống](#5-hướng-dẫn-biên-dịch--nạp-hệ-thống)
6. [Hướng Dẫn Sử Dụng Chương Trình Kiểm Thử (Laptop Test Tool)](#6-hướng-dẫn-sử-dụng-chương-trình-kiểm-thử-laptop-test-tool)
7. [Các Tính Năng Nổi Bật Đã Hiện Thực](#7-các-tính-năng-nổi-bật-đã-hiện-thực)
8. [Hướng Dẫn Xử Lý Sự Cố (Troubleshooting & FAQ)](#8-hướng-dẫn-xử-lý-sự-cố-troubleshooting--faq)
9. [Lộ Trình Nâng Cấp Kế Tiếp (Roadmap)](#9-lộ-trình-nâng-cấp-kế-tiếp-roadmap)

---

## 1. Kiến Trúc Tổng Thể Hệ Thống

Hệ thống được xây dựng theo mô hình **System-on-Chip (SoC)** hiện đại:

```
+-----------------------------------------------------------------------------------------+
|                                    FPGA DE2-115                                         |
|                                                                                         |
|  +---------------------+        +--------------------+        +---------------------+   |
|  |   CPU Nios V/m      |        |   40 KB On-Chip    |        |    Avalon-to-APB    |   |
|  | (32-bit RISC-V core)| <----> |     RAM (HEX)      | <----> |       Bridge        |   |
|  +---------------------+        +--------------------+        +----------+----------+   |
|            ^                                                             |              |
|            | Avalon Memory-Mapped Bus (50 MHz)                           | APB3 Bus     |
|            +-------------------------------------------------------------+              |
|                                                                          v              |
|                                                            +-------------------------+  |
|                                                            |    APB UART SLAVE       |  |
|                                                            |  (Registers: 0x00-0x10) |  |
|                                                            +------------+------------+  |
|                                                                         |               |
|                                                +------------------------+---------------+
|                                                |                        |               |
|                                                v                        v               |
|                                      +------------------+     +------------------+      |
|                                      |   UART TX CORE   |     |   UART RX CORE   |      |
|                                      | (FSM Phát khung) |     | (16x Over-sample)|      |
|                                      +--------+---------+     +---------+--------+      |
|                                               |                         ^               |
+-----------------------------------------------|-------------------------|---------------+
                                                | TX (Pin AB22)           | RX (Pin AC15)
                                                v                         |
                                          +-------------------------------------+
                                          |    MẠCH CHUYỂN ĐỔI USB - UART       |
                                          |     (CP2102 / CH340 / FTDI)         |
                                          +------------------+------------------+
                                                             | USB Cable
                                                             v
                                                  +----------------------+
                                                  |   LAPTOP PC HOST     |
                                                  |  (Python CLI Tool)   |
                                                  +----------------------+
```

### Thành phần chính:
* **Khối xử lý trung tâm (Nios V/m)**: CPU RISC-V 32-bit hoạt động tại tần số 50 MHz (`PIN_Y2`), chạy firmware C bare-metal trong On-Chip RAM 40 KB.
* **Avalon-to-APB Bridge**: Cầu chuyển đổi giao thức bus từ chuẩn Intel Avalon-MM sang chuẩn bus công nghiệp ARM AMBA APB3.
* **Bộ sinh Baudrate (`uart_baudrate`)**: Chia xung 50 MHz sang tốc độ chuẩn 115200 bps:
  * Xung nhịp phát TX: $OS_{TX} = 1\times$ Baudrate.
  * Xung nhịp lấy mẫu RX: $OS_{RX} = 16\times$ Baudrate (khử nhiễu và định vị chính xác giữa bit tại `os_mid = 7`).
* **Khối phát UART (`uart_tx`)**: FSM điều khiển tự động truyền bit Start, dữ liệu động (5, 6, 7 hoặc 8 bit), bit Parity (Even/Odd), và bit Stop (1 hoặc 2 bit).
* **Khối nhận UART (`uart_rx`)**: Đồng bộ 2 tầng Flip-Flop chống hiện tượng siêu ổn định (Metastability), tích lũy kiểm tra Parity phần cứng thời gian thực, phát hiện lỗi khung (`frame_error`) và lỗi chẵn lẻ (`parity_error`).

---

## 2. Bản Đồ Thanh Ghi APB (Memory Map & Registers)

Hệ thống APB UART Slave được ánh xạ bắt đầu từ Base Address: **`0x00022000`**.

| Tên Thanh Ghi | Offset | Quyền | Kích thước | Mô Tả Chức Năng |
| :--- | :---: | :---: | :---: | :--- |
| **`REG_UART_TX_DATA`** | `0x000` | Write | 8-bit | Ghi byte dữ liệu cần truyền ra đường truyền nối tiếp |
| **`REG_UART_RX_DATA`** | `0x004` | Read | 8-bit | Đọc byte dữ liệu nhận được (tự động xóa cờ `RX_DONE`) |
| **`REG_UART_CFG`** | `0x008` | R/W | 8-bit | Cấu hình khung truyền: Data bits, Stop bits, Parity |
| **`REG_UART_CTRL`** | `0x00C` | Write | 8-bit | Điều khiển phần cứng: Bit 0 = `START_TX` (kích hoạt phát) |
| **`REG_UART_STATUS`** | `0x010` | Read | 8-bit | Trạng thái: `TX_DONE`, `RX_DONE`, `PARITY_ERROR` |

### Chi tiết các trường bit trong `REG_UART_CFG` (Offset `0x008`):
* **Bit [1:0] - Data Bits (`DATA_NUM`)**:
  * `00`: 5 bit dữ liệu
  * `01`: 6 bit dữ liệu
  * `10`: 7 bit dữ liệu
  * `11`: 8 bit dữ liệu
* **Bit [2] - Stop Bits (`STOP_NUM`)**:
  * `0`: 1 Stop bit
  * `1`: 2 Stop bits
* **Bit [3] - Parity Enable (`PARITY_EN`)**:
  * `0`: Không sử dụng bit Parity (None)
  * `1`: Bật kiểm tra bit Parity
* **Bit [4] - Parity Type (`PARITY_TYPE`)**:
  * `0`: Parity Lẻ (Odd Parity)
  * `1`: Parity Chẵn (Even Parity)

#### Các giá trị cấu hình khung truyền chuẩn:
| Tên Cấu Hình | Giá Trị Hex | Số Bit Dữ Liệu | Parity | Số Bit Stop |
| :---: | :---: | :---: | :---: | :---: |
| **`8N1`** *(Mặc định)* | `0x03` | 8 | Không | 1 |
| **`8E1`** | `0x1B` | 8 | Chẵn (Even) | 1 |
| **`8O1`** | `0x0B` | 8 | Lẻ (Odd) | 1 |
| **`7E1`** | `0x1A` | 7 | Chẵn (Even) | 1 |
| **`7O1`** | `0x0A` | 7 | Lẻ (Odd) | 1 |
| **`8N2`** | `0x07` | 8 | Không | 2 |

### Chi tiết các cờ trong `REG_UART_STATUS` (Offset `0x010`):
* **Bit 0 - `TX_DONE`**: Bằng `1` khi bộ phát rảnh/đã hoàn tất truyền byte trước đó; bằng `0` khi đang bận truyền.
* **Bit 1 - `RX_DONE`**: Bằng `1` khi bộ nhận đã nhận trọn vẹn 1 khung byte và lưu vào bộ đệm; tự động clear về `0` khi CPU đọc thanh ghi `REG_UART_RX_DATA`.
* **Bit 2 - `PARITY_ERROR`**: Bằng `1` khi phát hiện khung nhận bị sai lệch bit kiểm tra Parity; bằng `0` khi khung truyền toàn vẹn.

---

## 3. Cấu Trúc Thư Mục Dự Án

```text
UART/
├── docs/                                  # Tài liệu đặc tả và thiết kế
│   ├── apb_uart_upgrade_roadmap.md        # Lộ trình nâng cấp chi tiết (FIFO, Baud, Switch)
│   ├── dac-ta-ky-thuat-apb-uart.docx      # Bản đặc tả kỹ thuật đồ án
│   └── final_project_design_requirements...# Yêu cầu thiết kế từ giảng viên
├── firmware/                              # Mã nguồn phần mềm điều khiển trên Nios V & PC
│   ├── app/                               # Thư mục build CMake cho Nios V
│   ├── bsp/                               # Board Support Package sinh từ Qsys
│   ├── apb_uart_regs.h                    # Định nghĩa địa chỉ và bitmask thanh ghi APB
│   ├── apb_uart.h / apb_uart.c            # Driver HAL điều khiển phần cứng UART
│   ├── main.c                             # Firmware tương tác: Menu, Bit test, Echo đệm dòng
│   ├── laptop_test.py                     # Ứng dụng Python điều khiển, kiểm thử và đồng bộ COM
│   ├── build_firmware.bat                 # Script tự động compile C -> nhúng HEX vào .SOF
│   └── download_firmware.bat              # Script nạp firmware qua niosv-download
├── quartus/                               # Dự án Quartus Prime Lite Edition
│   ├── output_files/                      # Chứa file bitstream nạp FPGA (apb_uart.sof)
│   ├── system/ & system.qsys              # Thiết kế hệ thống Nios V trong Platform Designer
│   ├── apb_uart.qsf                       # Gán chân FPGA (Pin assignments) và thông số dự án
│   ├── apb_uart.sdc                       # Ràng buộc thời gian (Timing constraints 50 MHz)
│   ├── build_system.tcl                   # Script tự động tạo hệ thống Qsys
│   └── program_fpga.bat                   # Script 1-click nạp nhanh bitstream vào kit DE2
├── rtl/                                   # Mã nguồn phần cứng Verilog HDL
│   ├── apb_uart.v                         # Top-level module kết nối Nios V và APB UART
│   ├── avalon_to_apb_bridge.v             # Cầu nối Avalon Slave sang APB Master
│   ├── uart_core.v                        # Bộ điều khiển trung tâm UART
│   ├── RX/                                # Khối nhận UART (Datapath, Controller FSM)
│   ├── TX/                                # Khối phát UART (Datapath, Controller FSM)
│   └── interface_uart/                    # Khối APB Slave Interface giải mã thanh ghi
├── tb/                                    # Testbench mô phỏng kiểm thử phần cứng
└── README.md                              # Tài liệu hướng dẫn sử dụng dự án
```

---

## 4. Sơ Đồ Kết Nối Phần Cứng (Hardware Pinout)

Hệ thống sử dụng các chân GPIO thuộc đầu cắm **JP5** trên bo mạch DE2-115 để kết nối với mạch chuyển đổi USB-UART:

| Tín Hiệu | Chân FPGA (Cyclone IV) | Vị Trí Header JP5 | Kết Nối Với Mạch USB-UART | Ghi Chú |
| :--- | :---: | :---: | :---: | :--- |
| **`UART_TX`** | `PIN_AB22` | **Pin 1** | **RXD** | Chân truyền từ FPGA sang Laptop *(Đấu chéo)* |
| **`UART_RX`** | `PIN_AC15` | **Pin 3** | **TXD** | Chân nhận từ Laptop vào FPGA *(Đấu chéo)* |
| **`GND`** | `GND` | **Pin 12** | **GND** | Chân nối đất chung bắt buộc |
| **`CLOCK_50`**| `PIN_Y2` | Trực tiếp trên bo | — | Dao động thạch anh 50 MHz |
| **`RESET_N`** | `PIN_M23` (`KEY[0]`) | Trực tiếp trên bo | — | Nút nhấn Reset hệ thống (Active-Low) |

> ⚠️ **Lưu ý quan trọng**: Tuyệt đối phải đấu **chéo** chân (`TX -> RXD`, `RX -> TXD`) và nối dây **GND** chung giữa bo mạch DE2-115 và mạch USB-UART. Không cấp nguồn 5V/3.3V từ USB-UART vào chân GPIO của FPGA.

---

## 5. Hướng Dẫn Biên Dịch & Nạp Hệ Thống

Dự án đã được tích hợp đầy đủ công cụ tự động hóa, người dùng có thể thực hiện mọi thao tác qua dòng lệnh terminal hoặc batch script:

### 5.1. Nạp Bitstream vào FPGA (Bao gồm Phần cứng + Firmware C)
Chỉ cần chạy lệnh sau từ thư mục gốc của dự án:
```powershell
e:\Lab_EDABK\TKS_slide\BTGK_UART\UART\quartus\program_fpga.bat nowait
```
Script sẽ tự động tìm cáp **USB-Blaster** và nạp file `output_files/apb_uart.sof` vào chip FPGA.

### 5.2. Chỉnh Sửa và Biên Dịch Lại Firmware C
Khi bạn chỉnh sửa mã nguồn C trong [firmware/main.c](file:///e:/Lab_EDABK/TKS_slide/BTGK_UART/UART/firmware/main.c):
```powershell
e:\Lab_EDABK\TKS_slide\BTGK_UART\UART\firmware\build_firmware.bat nowait
```
Quá trình build diễn ra hoàn toàn tự động:
1. Trình biên dịch `riscv32-unknown-elf-gcc` biên dịch `main.c` thành `apb_uart.elf`.
2. Công cụ `elf2hex` sinh file bộ nhớ `system_on_chip_mem.hex`.
3. Công cụ Quartus `quartus_cdb` cập nhật trực tiếp nội dung RAM vào file `.sof` mà **không cần phải biên dịch lại toàn bộ phần cứng Quartus** (chỉ mất ~5 giây).
4. Chạy lại `program_fpga.bat nowait` để đưa code mới lên bo mạch.

---

## 6. Hướng Dẫn Chạy Chương Trình & Kiểm Thử Hệ Thống (Quick Start Guide)

Dự án hỗ trợ chế độ tương tác **2 Cửa Sổ Song Song (Dual-Terminal Laptop ⮂ FPGA)** chuyên nghiệp, trực quan nhất cho báo cáo và nghiệm thu đồ án:
* **Cửa Sổ Trái (Laptop Terminal)**: Đại diện cho trạm máy tính phát / thu.
* **Cửa Sổ Phải (FPGA Terminal)**: Đại diện cho bo mạch FPGA DE2-115 (CPU RISC-V Nios V & APB UART).

---

### 🚀 3 Bước Khởi Động Nhanh (Chỉ mất 30 giây):

#### Bước 1: Kết nối phần cứng bo mạch DE2-115
1. Cắm cáp **USB-Blaster** và bật nút đỏ `POWER` trên bo mạch DE2-115.
2. Cắm mạch chuyển đổi USB-UART (CH340/CP2102/FTDI) vào cổng USB laptop.
3. Đấu nối 3 dây vật lý vào hàng cắm mở rộng **Header JP5** trên DE2-115:
   * **`PIN_AB22`** (Header JP5 - Pin 1, `UART_TX`) $\longrightarrow$ nối vào chân **`RXD`** của mạch USB-UART.
   * **`PIN_AC15`** (Header JP5 - Pin 3, `UART_RX`) $\longrightarrow$ nối vào chân **`TXD`** của mạch USB-UART.
   * **`GND`** (Header JP5 - Pin 12) $\longrightarrow$ nối vào chân **`GND`** của mạch USB-UART.

#### Bước 2: Nạp Bitstream vào FPGA (Phần cứng + Code C)
Mở terminal và chạy lệnh nạp bitstream `.sof` đã tích hợp sẵn firmware:
```cmd
e:\Lab_EDABK\TKS_slide\BTGK_UART\UART\quartus\program_fpga.bat nowait
```
*(Thông báo `NAP BITSTREAM SOF THANH CONG!` hiện ra xác nhận FPGA đã sẵn sàng).*

#### Bước 3: Khởi động 2 Terminal Song Song
Chỉ cần nhấp đúp chuột vào file batch:
```cmd
e:\Lab_EDABK\TKS_slide\BTGK_UART\UART\firmware\dual_terminal\run_dual_terminals.bat
```
Hoặc từ cửa sổ dòng lệnh PowerShell/CMD:
```powershell
cd e:\Lab_EDABK\TKS_slide\BTGK_UART\UART\firmware\dual_terminal
.\run_dual_terminals.bat
```

> **Cơ chế tự động**: File batch sẽ tự động:
> 1. Mở **Cửa sổ Phải** (`terminal_fpga.py`), quét và tự động mở cổng COM (thường là `COM5` ở 115200, 8N1), sau đó ghim vào nửa phải màn hình.
> 2. Mở **Cửa sổ Trái** (`terminal_laptop.py`), kết nối vào Socket IPC nội bộ (`127.0.0.1:9876`) và tự động ghim vào nửa trái màn hình.
> 3. Cả 2 cửa sổ đồng bộ cấu hình khung truyền ban đầu `8N1`.

---

### 📋 Quy Tắc Hiển Thị Đơn Biên (Single-Sided RX Display Rule)
Nhằm đảm bảo giao diện gọn gàng, trực quan và không bị lặp chữ:
* Khi **Laptop phát**: Màn hình Laptop **chỉ hiện khung ĐÃ PHÁT** (màu xanh dương). Màn hình FPGA là nơi duy nhất **hiển thị khung ĐÃ NHẬN** (màu xanh lá) kèm phân tích Bit 7 và kiểm tra Parity.
* Khi **FPGA phát**: Màn hình FPGA **chỉ hiện khung ĐÃ PHÁT** (màu vàng). Màn hình Laptop là nơi duy nhất **hiển thị khung ĐÃ NHẬN** (màu xanh lá) kèm kết quả kiểm tra Parity.
* Tuyệt đối không in trùng lặp thông tin nhận tại bên phát.

---

#### 🔄 Các Kịch Bản Kiểm Thử Trực Tiếp (Không Cần Qua Menu):

##### 1. Chiều Laptop (Trái) ➡️ FPGA (Phải):
* **Truyền bit nhị phân (vd: `10101010b`, `10100101b`, `0100101b`)**:
  * Tại dấu nhắc `Laptop_TX>`, gõ: `10101010b` (hoặc `10100101b`).
  * **Ô Trái (Laptop)**: Hiện khung màu Cyan `[LAPTOP ĐÃ PHÁT TÍN HIỆU SANG FPGA]`:
    - Giá trị Hex: `0xAA` | Dạng Binary: `10101010b` | Bit 7 (MSB): `1` | Parity phát đi.
  * **Ô Phải (FPGA)**: Lập tức nhận dữ liệu thực từ phần cứng và hiện khung màu Xanh lá `[FPGA ĐÃ NHẬN DỮ LIỆU TỪ LAPTOP]`:
    - Giá trị Hex: `0xAA` | Dạng Binary: `10101010b` | Bit 7 (MSB): `1` | Bit Parity nhận: `0` | Parity Check: `✅ CHÍNH XÁC (PAR_ERR = 0)`.
* **Truyền mã Hex (vd: `0xAA`, `0xA5`, `0xFF`, `AA`)**:
  * Tại ô Trái, gõ: `0xA5` $\rightarrow$ Ô Phải nhận và phân tích chi tiết.
* **Truyền chuỗi ký tự (vd: `abc`, `hello`, `FPGA DE2`)**:
  * Tại ô Trái, gõ: `hello` $\rightarrow$ Ô Trái hiện khung phát chuỗi $\rightarrow$ Ô Phải hiện khung nhận chuỗi kèm độ dài 5 byte và kiểm tra lỗi Parity.

##### 2. Chiều FPGA (Phải) ➡️ Laptop (Trái):
* **FPGA phát bit nhị phân / mã Hex**:
  * Tại dấu nhắc `FPGA_TX>`, gõ: `10101010b` (hoặc `0x55`).
  * **Ô Phải (FPGA)**: Hiện khung màu Vàng `[FPGA ĐÃ PHÁT TÍN HIỆU SANG LAPTOP]`. CPU Nios V gửi byte ra chân vật lý `PIN_AB22`.
  * **Ô Trái (Laptop)**: Lập tức hiện khung màu Xanh lá `[LAPTOP ĐÃ NHẬN DỮ LIỆU TỪ FPGA]`:
    - Giá trị: `0x55` | Binary: `01010101b` | Bit 7: `0` | Parity: `✅ CHÍNH XÁC`.
* **FPGA phát chuỗi văn bản**:
  * Tại ô Phải, gõ: `hello from fpga` $\rightarrow$ Ô Phải hiện khung phát $\rightarrow$ Ô Trái hiện khung nhận chuỗi.

##### 3. Đổi cấu hình khung truyền đồng bộ 1-chạm (`8e1`, `8o1`, `8n1`, `7e1`, `7o1`, `8n2`):
* Tại **bất kỳ cửa sổ nào** (Trái hoặc Phải), chỉ cần gõ tên cấu hình:
  * `8e1` $\rightarrow$ Cả 2 bên cùng đổi sang: 8 Data bits, Even Parity, 1 Stop bit.
  * `8o1` $\rightarrow$ Cả 2 bên cùng đổi sang: 8 Data bits, Odd Parity, 1 Stop bit.
  * `7e1` $\rightarrow$ Cả 2 bên cùng đổi sang: 7 Data bits, Even Parity, 1 Stop bit (tự động cắt bit 7 MSB).
  * `7o1` $\rightarrow$ Cả 2 bên cùng đổi sang: 7 Data bits, Odd Parity, 1 Stop bit.
  * `8n1` $\rightarrow$ Đưa cả 2 bên về cấu hình chuẩn ban đầu (No Parity).
* Thanh ghi phần cứng `REG_UART_CFG` (0x008) trên FPGA được cập nhật tức thời qua lệnh giao thức `!CFG:<MODE>`, đảm bảo **100% không bị lệch pha hay nhận sai giá trị**.

---

### 6.2. Chế Độ Console Đơn (Single-Terminal Tool)

Nếu muốn quay về sử dụng một cửa sổ dòng lệnh tương tác duy nhất như ban đầu:
```powershell
python e:/Lab_EDABK/TKS_slide/BTGK_UART/UART/firmware/laptop_test.py
```

#### Menu 5 Chức Năng Chính:
```text
========================================
   FPGA DE2 - APB UART SYSTEM [115200]  
   Cau hinh: 8N1 (CFG = 0x03)
========================================
 [1] Phat du lieu chu dong: FPGA -> Laptop
 [2] Test truyen Bit 0/1 & Hex (0x00-0xFF)
 [3] Test truyen Ky tu / Chuoi (Text Echo)
 [4] Xem trang thai thanh ghi APB
 [5] Doi cau hinh (8N1, 8E1, 8O1, 7E1, 7O1, 8N2)
========================================
Chon [1-5]: 
```

* **Chế độ 1 (FPGA -> Laptop)**: Hỗ trợ phát chuỗi tùy chọn (`Custom String`), phát byte tùy chọn (`Custom Byte`), Burst 5 gói tin, Telemetry và bảng mã Ramp 256-byte.
* **Chế độ 2 (Laptop -> FPGA)**: Kiểm tra bit 7 (MSB) và cờ `PARITY_ERROR`. Hỗ trợ phím thoát: bấm **`ESC`** hoặc **`Ctrl+C`** (giải phóng hoàn toàn mã byte `0x71` để kiểm tra dữ liệu bình thường).
* **Chế độ 3 (Text Echo)**: Đệm dòng chống tràn, echo chính xác 100% chuỗi văn bản dài.
* **Chế độ 4 (Status Register)**: Đọc tức thời giá trị thanh ghi `CFG` và `STATUS`.
* **Chế độ 5 (Change Config)**: Đổi cấu hình phần cứng FPGA giữa 6 chế độ: `8N1`, `8E1`, `8O1`, `7E1`, `7O1`, `8N2`.

---

## 7. Các Tính Năng & Sửa Lỗi Quan Trọng (Bug Fixes)

1. **Khắc phục lỗi nhận sai tín hiệu khi cấu hình Parity (8O1, 7E1, 7O1)**:
   * **Nguyên nhân cũ**: 
     - *Lệch pha do điều hướng menu bằng phím*: Trước đây việc đổi cấu hình dựa vào việc gửi phím giả lập (`ESC`, `5`, số lựa chọn) vào menu văn bản của CPU Nios V. Khi CPU đang ở vòng lặp test, các ký tự này bị nuốt thành byte dữ liệu (`0x35`, `0x33`), khiến FPGA giữ nguyên `8N1` (`0x03`) trong khi Laptop đã đổi sang `8O1` hoặc `7O1`. Khi đó, bit Parity của Laptop bị FPGA đọc thành bit 7 MSB của dữ liệu (ví dụ `10100101b` bị mất bit thành `0x25` hoặc `'q'` thành `0xF1`) và báo `Parity: NONE`.
     - *Xóa sớm cờ Parity*: Trong RTL `apb_datapath.v`, thao tác đọc thanh ghi `REG_UART_RX_DATA` (0x004) kích hoạt `clear_rx_done` và xóa cờ `parity_error` về 0. Firmware cũ đọc `RX_DATA` trước khi đọc `STATUS`, khiến cờ lỗi Parity luôn bị xóa mất.
   * **Khắc phục triệt để**:
     - Thiết kế **Tầng Giao Thức Tốc Độ Cao** (Fast Protocol Layer): Cấu hình được đổi trực tiếp thông qua lệnh `!CFG:<MODE>` (`!CFG:8E1`, `!CFG:8O1`, `!CFG:7E1`...). Nios V bắt lệnh tức thì và ghi trực tiếp thanh ghi `REG_UART_CFG` (0x008), không còn thông qua menu văn bản, loại bỏ 100% rủi ro lệch pha.
     - Hàm `apb_uart_receive_byte` trong `apb_uart.c` đọc và lưu trạng thái `parity_error` từ `REG_UART_STATUS` (0x010) **trước khi** đọc `REG_UART_RX_DATA` (0x004), bảo toàn nguyên vẹn cờ Parity từ phần cứng RTL.
2. **Khắc phục triệt để lỗi Laptop truyền sang FPGA nhưng FPGA không hiện đã nhận**:
   * **Nguyên nhân gốc rễ 1 (Lệch Bitstream SOF)**: Sau khi chạy tổng hợp `quartus_map`, cơ sở dữ liệu Fitter bị vô hiệu hóa khiến script `build_firmware.bat` (do chặn log bằng `>nul`) không build được file `.sof` mới. Bo mạch DE2-115 vẫn nạp file SOF cũ chứa menu nhập phím [1-5], nên khi Laptop truyền byte hoặc chuỗi sang, FPGA coi đó là lựa chọn menu không hợp lệ và không thể hiển thị kết quả. -> *Đã khắc phục: Chạy `quartus_fit` và tự động cập nhật chuẩn xác bitstream `.sof`.*
   * **Nguyên nhân gốc rễ 2 (Hàm trễ làm mất byte UART ở 115200 bps)**: Ở tốc độ 115200 baud, 1 byte truyền mất 87µs. Việc chèn `delay_cycles(5000)` (~100µs) trong vòng lặp nhận chuỗi/lệnh khiến CPU Nios V bị lỡ nhịp và nuốt mất byte tiếp theo từ PC. -> *Đã khắc phục: Thay thế bằng cơ chế **Tight Polling** 50MHz siêu nhạy, bắt kịp 100% byte dữ liệu và chuỗi text.*
   * **Nguyên nhân gốc rễ 3 (Xung đột buffer nối tiếp)**: Cửa sổ FPGA nuốt các byte echo rác đứng trước dấu `!` và bổ sung `ser.flush()` đảm bảo đẩy dữ liệu vật lý tức thì sang kit DE2.
3. **Khắc phục hiện tượng lặp lại thông tin (Single-Sided RX Display Rule)**:
   - Hệ thống tuân thủ nghiêm ngặt quy tắc đơn biên: Khi Bên A phát, Bên A **chỉ hiện khung ĐÃ PHÁT**; duy nhất Bên B **hiện khung ĐÃ NHẬN kèm phân tích Bit 7 và Parity**. Tuyệt đối không có phản hồi thừa hay lặp lại.
4. **Loại bỏ lỗi ký tự rác / Unicode khi chạy 7-bit**: Tự động áp dụng mặt nạ `0x7F` (`b & 0x7F`) tại tầng nhận dữ liệu của Python, loại bỏ hoàn toàn các ký tự lạ hoặc dấu hỏi khi chuyển đổi bảng mã.
5. **Hiển thị tường minh Bit Parity**: Hệ thống tự động tính toán tổng số bit `1` của data và hiển thị giá trị bit Parity thực tế trên đường truyền vật lý, giúp việc học tập và đối soát giao thức UART trở nên trực quan.

---

## 8. Hướng Dẫn Xử Lý Sự Cố (Troubleshooting & FAQ)

### 8.1. Lỗi nhận sai dữ liệu hoặc FPGA không phản hồi sau khi cắm lại kit
* **Nguyên nhân**: Bo mạch DE2-115 chứa bitstream `.sof` trong bộ nhớ SRAM khả biến (Volatile SRAM). Khi tắt nguồn kit hoặc rút cáp USB cấp nguồn, bitstream trong SRAM sẽ bị mất hoàn toàn, chip Cyclone IV trở về trạng thái chưa nạp.
* **Cách khắc phục**:
  1. Cắm cáp nạp USB-Blaster và bật công tắc nguồn `POWER` màu đỏ trên kit DE2-115.
  2. Chạy lệnh nạp lại bitstream:
     ```powershell
     e:\Lab_EDABK\TKS_slide\BTGK_UART\UART\quartus\program_fpga.bat nowait
     ```
  3. Khởi động lại `terminal_fpga.py` và `terminal_laptop.py` (hoặc `laptop_test.py`).

### 8.2. Lỗi `could not open port 'COMx': FileNotFoundError(2, ...)`
* **Nguyên nhân**: Cáp chuyển đổi USB-UART bị lỏng hoặc nhận nhầm cổng `COM3` ảo của bo mạch chủ thay vì cổng COM của cáp USB-UART (`COM4`).
* **Cách khắc phục**:
  1. Rút cáp USB-UART ra và cắm chặt lại vào cổng USB trên Laptop.
  2. Mở **Device Manager** $\rightarrow$ xem cổng COM thực của cáp USB-UART (thường là `COM4`).
  3. Khi script hỏi cổng COM, chọn đúng cổng này.

### 8.3. Lỗi `PermissionError: [Errno 13] Access is denied: 'COMx'`
* **Nguyên nhân**: Cổng COM đang bị một chương trình khác chiếm dụng độc quyền (như một cửa sổ terminal cũ chưa tắt).
* **Cách khắc phục**: Đóng các cửa sổ terminal hoặc phần mềm serial đang chạy ngầm trước đó, sau đó khởi động lại script.

### 8.4. Lưu ý đấu nối dây vật lý Header JP5
* **Luôn đấu chéo chân**:
  * `PIN_AB22` (`UART_TX` - JP5 Pin 1) $\longrightarrow$ nối vào **`RXD`** của mạch USB-UART.
  * `PIN_AC15` (`UART_RX` - JP5 Pin 3) $\longrightarrow$ nối vào **`TXD`** của mạch USB-UART.
* **Nối chung GND**: Bắt buộc nối chân **`GND`** (JP5 Pin 12) với chân `GND` của mạch USB-UART để có cùng điện thế tham chiếu.

---

## 9. Lộ Trình Nâng Cấp Kế Tiếp (Roadmap)

Dự án đã sẵn sàng kiến trúc để phát triển thêm các tính năng nâng cao trong các giai đoạn tiếp theo (xem chi tiết tại [docs/apb_uart_upgrade_roadmap.md](file:///e:/Lab_EDABK/TKS_slide/BTGK_UART/UART/docs/apb_uart_upgrade_roadmap.md)):

* **Giai đoạn 1: Bộ đệm phần cứng FIFO & Đèn LED báo trạng thái**
  * Tích hợp 16-byte FIFO cho khối RX và TX bằng khối RAM nhúng (M9K).
  * Điều khiển `LEDG[0]` (nháy khi nhận RX), `LEDG[1]` (nháy khi phát TX), `LEDR[0]` (báo lỗi Parity).
* **Giai đoạn 2: Điều chỉnh Baudrate Động (`REG_BAUD_DIV`)**
  * Bổ sung thanh ghi cấu hình hệ số chia tần `BAUD_DIV` tại địa chỉ APB `0x014`, cho phép phần mềm thay đổi linh hoạt tốc độ Baud từ 9600 đến 921600 bps trong lúc đang chạy.
* **Giai đoạn 3: Phát Dữ Liệu Trực Tiếp Từ Phần Cứng FPGA**
  * Sử dụng hệ thống công tắc gạt `SW[7:0]` làm dữ liệu phát 8-bit và nút nhấn `KEY[1]` làm xung kích hoạt phát trực tiếp từ phần cứng lên Laptop mà không cần thông qua CPU.

---

## 👨‍💻 Thông Tin Bản Quyền & Tác Giả
* **Môn học**: Thiết kế Hệ thống Số / Hệ thống Nhúng (SoC)
* **Đơn vị**: Lab EDABK - Đại học Bách Khoa Hà Nội
* **Nền tảng phát triển**: Intel Quartus Prime Lite 25.1 / Altera Cyclone IV E DE2-115 / Python 3.x / Nios V RISC-V Toolchain.