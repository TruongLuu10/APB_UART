# ĐẶC TẢ CÁC PHIÊN BẢN NÂNG CẤP HỆ THỐNG APB UART TRÊN FPGA DE2-115

Tài liệu này tổng hợp chi tiết thiết kế kỹ thuật, mã nguồn Verilog RTL, ánh xạ thanh ghi APB và firmware C cho 3 hướng nâng cấp tiếp theo của hệ thống **CPU Nios V <---> Avalon-to-APB Bridge <---> APB UART**.

---

## I. TỔNG QUAN PHIÊN BẢN HIỆN TẠI (BASELINE SYSTEM - PHIÊN BẢN DỰ PHÒNG)

Hệ thống hiện tại đã hoạt động ổn định và được lưu giữ làm **phiên bản chuẩn / dự phòng an toàn**:

```
[Laptop PC / Python] <---(UART: 115200 bps, Khung truyen dong)---> [Kit FPGA DE2-115]
                                                                        │
        ┌───────────────────────────────────────────────────────────────┘
        ▼
   [Chân RX/TX] 
        │
   [uart_core] <======(Bus APB4)======> [avalon_apb_bridge] <====(Bus Avalon)====> [CPU Nios V/m]
```

### Bản đồ thanh ghi APB hiện tại (Base Address: `0x00022000`):
| Offset | Tên thanh ghi | R/W | Chức năng hiện tại |
| :---: | :--- | :---: | :--- |
| `0x000` | `TX_DATA_REG` | W | Ghi byte dữ liệu 8-bit cần phát ra Laptop |
| `0x004` | `RX_DATA_REG` | R | Đọc byte nhận từ Laptop (Tự động xóa cờ `rx_done`) |
| `0x008` | `CFG_REG` | RW | Cấu hình khung truyền: Data bits (5-8), Stop bits (1-2), Parity (None/Even/Odd) |
| `0x00C` | `CTRL_REG` | W | Bit 0: `start_tx` (Phát xung bắt đầu gửi) |
| `0x010` | `STATUS_REG` | R | Bit 0: `tx_done`, Bit 1: `rx_done`, Bit 2: `parity_error` |

---

## II. NÂNG CẤP 1: TÍCH HỢP THANH GHI ĐIỀU CHỈNH ĐỘNG BAUDRATE (`baud_div_reg`)

### 1. Mục tiêu kỹ thuật
- **Vấn đề bản cũ:** Tốc độ Baudrate được chốt cứng bằng `parameter integer BAUDRATE = 115200` tại thời điểm tổng hợp Quartus (Synthesis-time). Muốn đổi sang 9600 hay 57600 bps phải sửa code Verilog và biên dịch lại Quartus (~5 phút).
- **Mục tiêu nâng cấp:** Thêm thanh ghi `BAUD_DIV_REG` trên bus APB để CPU Nios V (bằng code C) có thể đổi Baudrate tùy ý trong thời gian thực (Runtime) mà không cần nạp lại FPGA.

### 2. Công thức tính hệ số chia Baudrate
Tần số hệ thống: $F_{CLK} = 50\text{ MHz} = 50\,000\,000\text{ Hz}$.  
Hệ số Oversampling bộ thu: $OS_{RX} = 16$.  
Hệ số chia nạp vào thanh ghi:
$$D_{RX} = \frac{F_{CLK}}{16 \times \text{BAUDRATE}}$$

| Tốc độ Baud mong muốn | Giá trị nạp thanh ghi $D_{RX}$ | Giá trị HEX ghi vào APB | Sai số thực tế (%) |
| :---: | :---: | :---: | :---: |
| **115200 bps** | $\approx 27$ | `0x001B` | 0.46% (Chuẩn) |
| **57600 bps** | $\approx 54$ | `0x0036` | 0.46% (Chuẩn) |
| **38400 bps** | $\approx 81$ | `0x0051` | 0.46% (Chuẩn) |
| **19200 bps** | $\approx 163$ | `0x00A3` | 0.16% (Chuẩn) |
| **9600 bps** | $\approx 326$ | `0x0146` | 0.15% (Chuẩn) |

### 3. Thiết kế phần cứng RTL

#### A. Mở rộng thanh ghi trong `apb_datapath.v`:
```verilog
// 1. Khai báo thêm thanh ghi baud_div_reg (16-bit)
reg [15:0] baud_div_reg;
output wire [15:0] baud_div;
assign baud_div = baud_div_reg;

// 2. Thêm tín hiệu ghi decoder (Offset 0x014)
wire wr_baud_div_en = reg_wr_en && pstrb[0] && (paddr == 12'h014);

always @(posedge pclk or negedge presetn) begin
    if (!presetn) begin
        baud_div_reg <= 16'd27; // Mặc định 115200 bps khi khởi động
    end else if (wr_baud_div_en) begin
        baud_div_reg <= pwdata[15:0];
    end
end

// 3. MUX đọc dữ liệu prdata
case (paddr)
    12'h000: prdata = tx_data_reg;
    12'h004: prdata = rx_data_reg;
    12'h008: prdata = cfg_reg;
    12'h00C: prdata = ctrl_reg;
    12'h010: prdata = stt_reg;
    12'h014: prdata = {16'b0, baud_div_reg}; // Đọc lại hệ số chia
    default: prdata = 32'd0;
endcase
```

#### B. Nâng cấp khối `uart_baudrate.v`:
```verilog
module uart_baudrate (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [15:0] baud_div,      // Nhận giá trị chia động từ APB Datapath
    output reg         tx_tick_last,
    output reg         rx_tick_last
);
    wire [15:0] d_rx = (baud_div > 0) ? baud_div : 16'd27;
    wire [19:0] d_tx = d_rx * 16;     // Xung TX chậm hơn 16 lần so với xung RX 16x

    reg [19:0] count_tx;
    reg [15:0] count_rx;

    // Bộ đếm RX
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count_rx     <= 0;
            rx_tick_last <= 0;
        end else if (count_rx >= d_rx - 1) begin
            count_rx     <= 0;
            rx_tick_last <= 1;
        end else begin
            count_rx     <= count_rx + 1;
            rx_tick_last <= 0;
        end
    end

    // Bộ đếm TX
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count_tx     <= 0;
            tx_tick_last <= 0;
        end else if (count_tx >= d_tx - 1) begin
            count_tx     <= 0;
            tx_tick_last <= 1;
        end else begin
            count_tx     <= count_tx + 1;
            tx_tick_last <= 0;
        end
    end
endmodule
```

### 4. Nâng cấp Firmware C
```c
#define REG_UART_BAUD_DIV  APB_UART_REG(0x014)

void apb_uart_set_baudrate(uint32_t baudrate) {
    if (baudrate == 0) return;
    uint32_t div = 50000000u / (16u * baudrate);
    REG_UART_BAUD_DIV = div;
}
```

---

## III. NÂNG CẤP 2: TÍCH HỢP BỘ ĐỆM PHẦN CỨNG FIFO VÀ ĐÈN LED BÁO HOẠT ĐỘNG

### 1. Mục tiêu kỹ thuật
- **Vấn đề bản cũ:** Khi truyền liên tục chuỗi ký tự (như file hoặc paste đoạn text dài), CPU Nios V nếu bận xử lý sẽ gây ra lỗi tràn bộ nhận (**Receiver Overrun**).
- **Mục tiêu:**
  - Tích hợp **RX FIFO (16 hoặc 64 byte)**: Tự động lưu chuỗi ký tự đến, CPU rảnh lúc nào sẽ đọc lúc đó, loại bỏ hoàn toàn nguy cơ mất dữ liệu.
  - Tích hợp **TX FIFO (16 hoặc 64 byte)**: CPU đẩy cả chuỗi vào FIFO một lần rồi làm tác vụ khác, phần cứng tự động rút từng byte phát ra dây.
  - Tích hợp **Đèn LED nháy báo (Activity LEDs)**: Dùng mạch kéo dài xung (Pulse Stretcher) để hiển thị trực quan truyền/nhận lên LED trên kit DE2-115.

### 2. Kiến trúc khối FIFO trong RTL
```
[Bộ nhận uart_rx] ──(Push khi rx_done)──► [ RX FIFO 16x8 ] ◄──(Pop khi CPU doc 0x004)── [Bus APB]
                                               │
                                               └── Cờ: rx_empty, rx_full

[Bus APB] ──(Push khi CPU ghi 0x000)──► [ TX FIFO 16x8 ] ──(Pop tu dong)──► [Bộ phát uart_tx]
                                               │
                                               └── Cờ: tx_empty, tx_full
```

#### Module FIFO đồng bộ đơn giản (16 byte) bằng Verilog:
```verilog
module uart_fifo #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 4 // 2^4 = 16 byte
)(
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  wr_en,
    input  wire [DATA_WIDTH-1:0] wr_data,
    input  wire                  rd_en,
    output wire [DATA_WIDTH-1:0] rd_data,
    output wire                  empty,
    output wire                  full,
    output reg  [ADDR_WIDTH:0]   count
);
    reg [DATA_WIDTH-1:0] mem [(1<<ADDR_WIDTH)-1:0];
    reg [ADDR_WIDTH-1:0] wr_ptr;
    reg [ADDR_WIDTH-1:0] rd_ptr;

    assign empty   = (count == 0);
    assign full    = (count == (1<<ADDR_WIDTH));
    assign rd_data = mem[rd_ptr];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 0;
            rd_ptr <= 0;
            count  <= 0;
        end else begin
            case ({wr_en && !full, rd_en && !empty})
                2'b10: begin // Ghi
                    mem[wr_ptr] <= wr_data;
                    wr_ptr      <= wr_ptr + 1'b1;
                    count       <= count + 1'b1;
                end
                2'b01: begin // Đọc
                    rd_ptr      <= rd_ptr + 1'b1;
                    count       <= count - 1'b1;
                end
                2'b11: begin // Vừa ghi vừa đọc
                    mem[wr_ptr] <= wr_data;
                    wr_ptr      <= wr_ptr + 1'b1;
                    rd_ptr      <= rd_ptr + 1'b1;
                end
            endcase
        end
    end
endmodule
```

### 3. Mạch kéo dài xung điều khiển đèn LED (Pulse Stretcher)

Vì tốc độ truyền UART rất nhanh ($8.6\mu s/\text{bit}$), mắt người không nhìn thấy xung nháy. Cần kéo dài xung lên **$50\text{ ms}$** ($2.500.000$ chu kỳ ở $50\text{ MHz}$):

```verilog
module uart_led_activity (
    input  wire clk,
    input  wire rst_n,
    input  wire pulse_in,   // Tín hiệu kích hoạt (rx_done hoặc start_tx)
    output reg  led_out     // Đèn LED xuất ra chân bo mạch
);
    reg [21:0] timer;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            timer   <= 0;
            led_out <= 1'b0;
        end else if (pulse_in) begin
            timer   <= 22'd2500000; // Sáng trong 50ms
            led_out <= 1'b1;
        end else if (timer > 0) begin
            timer   <= timer - 1'b1;
            led_out <= 1'b1;
        end else begin
            led_out <= 1'b0;
        end
    end
endmodule
```

### 4. Gán chân LED trên kit DE2-115 (`apb_uart.qsf`)
| Tên tín hiệu | Chân FPGA | Loại linh kiện trên DE2-115 | Ý nghĩa hiển thị |
| :--- | :--- | :--- | :--- |
| `led_rx` | `PIN_E21` | **LEDG[0]** (Xanh lá) | Nhấp nháy mỗi khi nhận dữ liệu từ Laptop |
| `led_tx` | `PIN_E22` | **LEDG[1]** (Xanh lá) | Nhấp nháy mỗi khi FPGA phát dữ liệu về Laptop |
| `led_parity_err` | `PIN_G19` | **LEDR[0]** (Đỏ) | Bật sáng nếu phát hiện lỗi Parity |
| `led_fifo_full` | `PIN_F19` | **LEDR[1]** (Đỏ) | Bật sáng nếu RX FIFO bị đầy |

---

## IV. NÂNG CẤP 3: PHÁT DỮ LIỆU TRỰC TIẾP TỪ FPGA BẰNG SWITCH (SW) VÀ NÚT NHẤN (KEY)

### 1. Mục tiêu kỹ thuật
- Cho phép người thuyết trình / người dùng demo trực tiếp tại kit DE2:
  - Gạt 8 công tắc `SW[7:0]` để tạo giá trị byte dữ liệu nhị phân.
  - Bấm nút `KEY[1]` trên kit DE2.
  - Laptop lập tức nhận được ký tự tương ứng, in ra màn hình cả dạng ký tự, mã Hex và mã nhị phân.

### 2. Gán chân linh kiện trên DE2-115
```tcl
set_location_assignment PIN_AB28 -to sw[0]
set_location_assignment PIN_AC28 -to sw[1]
set_location_assignment PIN_AC27 -to sw[2]
set_location_assignment PIN_AD27 -to sw[3]
set_location_assignment PIN_AB27 -to sw[4]
set_location_assignment PIN_AC26 -to sw[5]
set_location_assignment PIN_AD26 -to sw[6]
set_location_assignment PIN_AB26 -to sw[7]
set_location_assignment PIN_M21  -to key1_n ; # Nút nhấn KEY[1] (Active-Low)
```

### 3. Mạch phát hiện nhấn phím (Debounce & Edge Detection) trong RTL
```verilog
// Mạch lấy mẫu 2 tầng chống metastability và phát hiện cạnh xuống nút nhấn KEY[1]
reg key1_ff1, key1_ff2, key1_last;
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        key1_ff1  <= 1'b1;
        key1_ff2  <= 1'b1;
        key1_last <= 1'b1;
    end else begin
        key1_ff1  <= key1_n;
        key1_ff2  <= key1_ff1;
        key1_last <= key1_ff2;
    end
end
wire key1_press = (key1_last == 1'b1 && key1_ff2 == 1'b0); // Cạnh xuống nhấn nút
```

### 4. Ánh xạ thanh ghi APB mới (`0x018`)
- **`0x018`** (`SW_KEY_REG` - Read Only):
  - Bit `[7:0]`: Giá trị của 8 switch `sw[7:0]`.
  - Bit `[8]`: Cờ `key1_pressed_flag` (tự động xóa sau khi CPU đọc).

### 5. Firmware C tương tác
```c
#define REG_UART_SW_KEY  APB_UART_REG(0x018)

void mode_switch_sender(void) {
    apb_uart_send_string("\r\n========================================================\r\n");
    apb_uart_send_string(" [CHE DO TRUYEN TU SWITCH / KEY TREN KIT DE2]\r\n");
    apb_uart_send_string(" -> Gat SW[7:0] de tao ma byte, nhan KEY[1] de truyen!\r\n");
    apb_uart_send_string(" -> Go 'q' tren Laptop de thoat che do.\r\n");
    apb_uart_send_string("========================================================\r\n\r\n");

    while (1) {
        // Kiểm tra xem Laptop có muốn thoát không
        uint8_t exit_char;
        if (apb_uart_receive_byte_nonblocking(&exit_char)) {
            if (exit_char == 'q' || exit_char == 0x1B) break;
        }

        // Đọc thanh ghi Switch & Key
        uint32_t val = REG_UART_SW_KEY;
        bool key_pressed = (val >> 8) & 0x1;
        uint8_t sw_data = (uint8_t)(val & 0xFF);

        if (key_pressed) {
            // 1. Phát byte qua UART về Laptop
            apb_uart_send_string("\r\n[FPGA KEY[1] PRESSED]:\r\n");
            apb_uart_send_string("  * Ky tu ASCII : '");
            apb_uart_send_byte(sw_data);
            apb_uart_send_string("'\r\n  * Ma Hex      : 0x");
            apb_uart_send_hex8(sw_data);
            apb_uart_send_string("\r\n  * Ma Binary   : ");
            for (int b = 7; b >= 0; b--) {
                apb_uart_send_byte(((sw_data >> b) & 1) ? '1' : '0');
            }
            apb_uart_send_string("b\r\n");
        }
    }
}
```

---

## V. BẢN ĐỒ THANH GHI APB TỔNG THỂ SAU KHI NÂNG CẤP TOÀN DIỆN

Sau khi nâng cấp cả 3 phần trên, không gian thanh ghi APB của ngoại vi UART sẽ hoàn chỉnh chuẩn công nghiệp:

| Offset | Tên thanh ghi | R/W | Bit fields | Ý nghĩa chức năng |
| :---: | :--- | :---: | :---: | :--- |
| `0x000` | `TX_DATA_REG` | W | `[7:0]` | Ghi dữ liệu cần phát (đẩy vào TX FIFO) |
| `0x004` | `RX_DATA_REG` | R | `[7:0]` | Đọc dữ liệu nhận (rút từ RX FIFO) |
| `0x008` | `CFG_REG` | RW | `[4:0]` | Cấu hình khung truyền (Data/Stop/Parity) |
| `0x00C` | `CTRL_REG` | W | `[1:0]` | Bit 0: `start_tx`, Bit 1: `flush_fifo` |
| `0x010` | `STATUS_REG` | R | `[7:0]` | Bit 0: `tx_done`, Bit 1: `rx_done`, Bit 2: `parity_err`,<br>Bit 3: `rx_empty`, Bit 4: `rx_full`, Bit 5: `tx_empty`, Bit 6: `tx_full` |
| `0x014` | `BAUD_DIV_REG` | RW | `[15:0]` | **Nâng cấp 1:** Cấu hình Baudrate động theo thời gian thực |
| `0x018` | `SW_KEY_REG` | R | `[8:0]` | **Nâng cấp 3:** Trạng thái các công tắc `SW[7:0]` và phím `KEY[1]` |

---

## VI. LỘ TRÌNH VÀ CHIẾN LƯỢC TRIỂN KHAI TỪNG BƯỚC

```
[Hiện tại: Baseline V1] (Line Buffering Firmware C - Đang chạy tốt)
          │
          ▼
    [Giai đoạn 1] Thêm Đèn LED báo Activity (LEDG[0], LEDG[1]) & Switch phát dữ liệu (Nâng cấp 2B + 3)
          │       --> Dễ làm nhất, không sửa khối UART lõi, thấy kết quả trực quan ngay trên kit DE2.
          ▼
    [Giai đoạn 2] Thêm thanh ghi BAUD_DIV_REG (Nâng cấp 1)
          │       --> Mở rộng thanh ghi APB, cho phép CPU đổi tốc độ baud.
          ▼
    [Giai đoạn 3] Tích hợp bộ đệm FIFO 16-byte vào TX/RX (Nâng cấp 2A)
                  --> Hoàn thiện hệ thống đạt chuẩn IP UART công nghiệp.
```

> [!TIP]
> **Quy tắc an toàn khi phát triển phần cứng FPGA:**
> Trước mỗi bước nâng cấp, bạn luôn giữ nguyên file `apb_uart.sof` hiện tại làm bản dự phòng. Chỉ cần chuyển sang bước tiếp theo khi bước trước đã được kiểm thử (simulation trên ModelSim/Questa và chạy thực tế trên bo mạch) đạt yêu cầu.
