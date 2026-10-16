#include "apb_uart.h"

void apb_uart_init(uint32_t config) {
    // 1. Cấu hình định dạng khung truyền UART (Data bits, Stop bits, Parity)
    REG_UART_CFG = config;
}

bool apb_uart_is_tx_ready(void) {
    // tx_done = 1 nghĩa là bộ phát UART rảnh rỗi hoặc vừa hoàn thành truyền
    return (REG_UART_STATUS & UART_STATUS_TX_DONE) != 0;
}

bool apb_uart_has_rx_data(void) {
    // rx_done = 1 nghĩa là bộ nhận UART đã thu thập đủ 1 byte vào thanh ghi
    return (REG_UART_STATUS & UART_STATUS_RX_DONE) != 0;
}

static volatile bool s_last_parity_error = false;

bool apb_uart_has_parity_error(void) {
    return s_last_parity_error;
}

uint32_t apb_uart_get_status(void) {
    return REG_UART_STATUS;
}

void apb_uart_send_byte(uint8_t byte) {
    // 1. Chờ cho tới khi bộ truyền TX sẵn sàng (tx_done == 1)
    while (!apb_uart_is_tx_ready()) {
        // Chờ bận (Polling)
    }

    // 2. Nạp byte dữ liệu vào thanh ghi tx_data_reg (Offset 0x000)
    REG_UART_TX_DATA = (uint32_t)byte;

    // 3. Kích hoạt phát dữ liệu bằng cách ghi bit start_tx vào ctrl_reg (Offset 0x00C)
    // Tín hiệu start_tx là dạng xung tự động xóa ở chu kỳ tiếp theo trong RTL
    REG_UART_CTRL = UART_CTRL_START_TX;
}

void apb_uart_send_string(const char *str) {
    if (!str) return;

    while (*str) {
        // Tự động chuyển '\n' thành "\r\n" để tương thích với Serial Terminal trên Windows PC
        if (*str == '\n') {
            apb_uart_send_byte('\r');
        }
        apb_uart_send_byte((uint8_t)*str);
        str++;
    }
}

uint8_t apb_uart_receive_byte(void) {
    // Chờ cho đến khi nhận được dữ liệu (rx_done == 1)
    while (!apb_uart_has_rx_data()) {
        // Chờ bận (Polling)
    }

    // Đọc cờ PARITY_ERROR từ STATUS (0x010) TRƯỚC KHI đọc RX_DATA (0x004)
    // vì thao tác đọc 0x004 sẽ kích hoạt clear_rx_done trong RTL và xóa parity_error về 0!
    s_last_parity_error = (REG_UART_STATUS & UART_STATUS_PAR_ERR) != 0;

    // Đọc byte dữ liệu từ rx_data_reg (Offset 0x004)
    // Lưu ý: Thao tác đọc thanh ghi 0x004 trong phần cứng RTL sẽ tự động kích hoạt
    // xung clear_rx_done để xóa cờ rx_done về 0, chuẩn bị đón nhận byte kế tiếp.
    return (uint8_t)(REG_UART_RX_DATA & 0xFFu);
}

bool apb_uart_receive_byte_nonblocking(uint8_t *byte) {
    if (apb_uart_has_rx_data()) {
        // Đọc cờ PARITY_ERROR TRƯỚC KHI đọc RX_DATA
        s_last_parity_error = (REG_UART_STATUS & UART_STATUS_PAR_ERR) != 0;
        if (byte) {
            *byte = (uint8_t)(REG_UART_RX_DATA & 0xFFu);
        }
        return true;
    }
    return false;
}

static inline void uart_delay(volatile uint32_t count) {
    while (count--) {
        __asm__ volatile ("nop");
    }
}

int apb_uart_read_line(char *buf, int max_len) {
    if (!buf || max_len <= 1) return 0;

    int count = 0;
    while (count < max_len - 1) {
        uint8_t c = apb_uart_receive_byte();

        // Ký tự kết thúc dòng (Enter từ PC có thể gửi '\r' hoặc '\n')
        if (c == '\r' || c == '\n') {
            // Hút sạch mọi ký tự ngắt dòng thừa (\r, \n) còn lại trong buffer
            for (int k = 0; k < 5; k++) {
                uart_delay(50000); // 1ms
                uint8_t extra;
                if (!apb_uart_receive_byte_nonblocking(&extra)) break;
            }
            apb_uart_send_string("\r\n"); // Echo xuống dòng cho PC
            break;
        }

        // Xử lý phím Backspace (xóa lùi ký tự)
        if (c == '\b' || c == 0x7F) {
            if (count > 0) {
                count--;
                apb_uart_send_string("\b \b"); // Xóa ký tự trên màn hình PC Terminal
            }
            continue;
        }

        // Ký tự in được thông thường: lưu vào buffer và Echo phản hồi lại màn hình PC
        if (c >= ' ' && c <= '~') {
            buf[count++] = (char)c;
            apb_uart_send_byte(c);
        }
    }

    buf[count] = '\0';
    return count;
}

static void apb_uart_send_hex_digit(uint8_t d) {
    d &= 0x0Fu;
    apb_uart_send_byte(d < 10 ? (uint8_t)('0' + d) : (uint8_t)('A' + (d - 10)));
}

void apb_uart_send_hex8(uint8_t val) {
    apb_uart_send_hex_digit(val >> 4);
    apb_uart_send_hex_digit(val);
}

void apb_uart_send_hex32(uint32_t val) {
    for (int i = 7; i >= 0; i--) {
        apb_uart_send_hex_digit((uint8_t)((val >> (i * 4)) & 0x0Fu));
    }
}

void apb_uart_send_dec(int32_t val) {
    if (val < 0) {
        apb_uart_send_byte('-');
        val = -val;
    }
    if (val == 0) {
        apb_uart_send_byte('0');
        return;
    }
    char buf[12];
    int idx = 0;
    while (val > 0) {
        buf[idx++] = (char)('0' + (val % 10));
        val /= 10;
    }
    while (idx > 0) {
        apb_uart_send_byte((uint8_t)buf[--idx]);
    }
}
