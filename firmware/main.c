/**
 * @file main.c
 * @brief Firmware điều khiển APB UART trên FPGA DE2 tối giản, tin cậy
 * @details Hỗ trợ:
 *          [1] Test truyền Bit nhị phân 0/1 (phân biệt rõ 7-bit và 8-bit MSB)
 *          [2] Test truyền Ký tự / Chuỗi (Text Echo)
 *          [3] Xem trạng thái thanh ghi APB
 *          [4] Đổi cấu hình khung truyền động (8N1, 8E1, 8O1, 7E1, 7O1, 8N2)
 */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include "apb_uart.h"

// Tạo trễ đơn giản cho CPU Nios V
static void delay_cycles(volatile uint32_t count) {
    while (count--) {
        __asm__ volatile ("nop");
    }
}

// In menu gọn gàng, tối giản
static void print_banner(void) {
    uint32_t cfg = REG_UART_CFG;
    int data_bits = (int)(cfg & 0x3) + 5;
    int stop_bits = (int)((cfg >> 2) & 0x1) + 1;
    int parity_en = (int)((cfg >> 3) & 0x1);
    int parity_type = (int)((cfg >> 4) & 0x1);
    char par_char = (!parity_en) ? 'N' : (parity_type ? 'E' : 'O');

    apb_uart_send_string("\r\n\r\n");
    apb_uart_send_string("========================================\r\n");
    apb_uart_send_string("   FPGA DE2 - APB UART SYSTEM [115200]  \r\n");
    apb_uart_send_string("   Cau hinh: ");
    apb_uart_send_dec(data_bits);
    apb_uart_send_byte((uint8_t)par_char);
    apb_uart_send_dec(stop_bits);
    apb_uart_send_string(" (CFG = 0x");
    apb_uart_send_hex8((uint8_t)cfg);
    apb_uart_send_string(")\r\n");
    apb_uart_send_string("========================================\r\n");
    apb_uart_send_string(" [1] Phat du lieu chu dong: FPGA -> Laptop\r\n");
    apb_uart_send_string(" [2] Test truyen Bit 0/1 & Hex (0x00-0xFF)\r\n");
    apb_uart_send_string(" [3] Test truyen Ky tu / Chuoi (Text Echo)\r\n");
    apb_uart_send_string(" [4] Xem trang thai thanh ghi APB\r\n");
    apb_uart_send_string(" [5] Doi cau hinh (8N1, 8E1, 8O1, 7E1, 7O1, 8N2)\r\n");
    apb_uart_send_string("========================================\r\n");
    apb_uart_send_string("Chon [1-5]: ");
}

// Trễ milli-giây cho CPU Nios V (50 MHz)
static void delay_ms(uint32_t ms) {
    while (ms--) {
        delay_cycles(50000);
    }
}

// Xóa sạch tất cả các byte còn tồn đọng trong buffer RX
static void apb_uart_flush_rx(void) {
    delay_cycles(150000);
    uint8_t trash;
    while (apb_uart_receive_byte_nonblocking(&trash)) {
        delay_cycles(50000);
    }
}

// Chuyển chuỗi số thành số nguyên (kèm giá trị mặc định)
static int parse_int(const char *str, int default_val) {
    if (!str || *str == '\0') return default_val;
    int res = 0;
    bool has_digit = false;
    while (*str == ' ' || *str == '\t') str++;
    while (*str >= '0' && *str <= '9') {
        res = res * 10 + (*str - '0');
        has_digit = true;
        str++;
    }
    return has_digit ? res : default_val;
}

// Phân tích chuỗi Hex (vd: 0xAA, FF) hoặc chuỗi nhị phân (vd: 10101010b) thành 1 byte
static uint8_t parse_byte(const char *str, uint8_t default_val) {
    if (!str || *str == '\0') return default_val;
    while (*str == ' ' || *str == '\t') str++;

    // Nhị phân: ví dụ 10101010 hoặc 10101010b
    int len = 0;
    while (str[len] == '0' || str[len] == '1') len++;
    if (len >= 7 && (str[len] == '\0' || str[len] == 'b' || str[len] == 'B' || str[len] == ' ')) {
        uint8_t val = 0;
        for (int i = 0; i < len; i++) {
            val = (val << 1) | (uint8_t)(str[i] - '0');
        }
        return val;
    }

    // Hex: ví dụ 0xAA hoặc AA
    if (str[0] == '0' && (str[1] == 'x' || str[1] == 'X')) {
        str += 2;
    }
    uint32_t hex_val = 0;
    bool has_hex = false;
    while (1) {
        char c = *str++;
        int d = -1;
        if (c >= '0' && c <= '9') d = c - '0';
        else if (c >= 'a' && c <= 'f') d = c - 'a' + 10;
        else if (c >= 'A' && c <= 'F') d = c - 'A' + 10;
        if (d >= 0) {
            hex_val = (hex_val << 4) | (uint32_t)d;
            has_hex = true;
        } else break;
    }
    return has_hex ? (uint8_t)(hex_val & 0xFF) : default_val;
}

// Chế độ 1: Cấu hình và phát dữ liệu chủ động từ FPGA -> Laptop
static void mode_fpga_transmit(void) {
    apb_uart_send_string("\r\n========================================\r\n");
    apb_uart_send_string(" [CAU HINH & PHAT DU LIEU: FPGA -> LAPTOP]\r\n");
    apb_uart_send_string("========================================\r\n");
    apb_uart_send_string(" [1] Phat chuoi ky tu tuy chon (Custom String)\r\n");
    apb_uart_send_string("     -> Tu do nhap chuoi, so lan phat, thoi gian tre\r\n");
    apb_uart_send_string(" [2] Phat Byte Hex / Nhi phan tuy chon (Custom Byte)\r\n");
    apb_uart_send_string("     -> Tu do nhap gia tri byte (0xAA, 10101010b...)\r\n");
    apb_uart_send_string(" [3] Phat 5 goi tin mau SoC kiem tra (Burst Test)\r\n");
    apb_uart_send_string(" [4] Phat luong giam sat dinh ky (Telemetry Stream)\r\n");
    apb_uart_send_string(" [5] Phat bang ma Ramp 256 Byte Hex (0x00 -> 0xFF)\r\n");
    apb_uart_send_string(" [q] Quay ve Menu chinh\r\n");
    apb_uart_send_string("========================================\r\n");
    apb_uart_send_string("Chon [1-5, q]: ");

    while (1) {
        char sub_buf[32];
        int sub_len = apb_uart_read_line(sub_buf, sizeof(sub_buf));
        if (sub_len == 0) {
            apb_uart_send_string("Chon [1-5, q]: ");
            continue;
        }

        char sub_choice = sub_buf[0];

        if (sub_choice == 'q' || sub_choice == 'Q' || sub_choice == 0x1B) {
            apb_uart_send_string("\r\n[THOAT] Quay ve Menu chinh!\r\n");
            print_banner();
            return;
        }

        if (sub_choice == '1') {
            // Cấu hình & phát chuỗi tùy chọn
            char custom_str[128];
            char num_buf[32];
            char delay_buf[32];

            apb_uart_send_string("\r\n\r\n--- [1] CAU HINH CHUOI KY TU MUON PHAT ---\r\n");
            apb_uart_send_string("1. Nhap chuoi (An Enter dung mac dinh \"Hello from FPGA DE2\"): ");
            apb_uart_flush_rx();
            int str_len = apb_uart_read_line(custom_str, sizeof(custom_str));
            if (str_len == 0) {
                strcpy(custom_str, "Hello from FPGA DE2 (Nios V 50MHz)");
                str_len = strlen(custom_str);
                apb_uart_send_string("(Mac dinh: \"");
                apb_uart_send_string(custom_str);
                apb_uart_send_string("\")\r\n");
            }

            apb_uart_send_string("2. Nhap so lan muon phat [1-20] (mac dinh 5): ");
            apb_uart_flush_rx();
            int n_len = apb_uart_read_line(num_buf, sizeof(num_buf));
            int repeat_cnt = (n_len > 0) ? parse_int(num_buf, 5) : 5;
            if (repeat_cnt < 1) repeat_cnt = 1;
            if (repeat_cnt > 20) repeat_cnt = 20;

            apb_uart_send_string("3. Khoang cach tre giua cac lan (ms) [100-2000] (mac dinh 500): ");
            apb_uart_flush_rx();
            int d_len = apb_uart_read_line(delay_buf, sizeof(delay_buf));
            int delay_val = (d_len > 0) ? parse_int(delay_buf, 500) : 500;
            if (delay_val < 50) delay_val = 50;
            if (delay_val > 5000) delay_val = 5000;

            apb_uart_send_string("\r\n[+] DA LUU CAU HINH PHAT:\r\n");
            apb_uart_send_string("  * Chuoi phat   : \"");
            apb_uart_send_string(custom_str);
            apb_uart_send_string("\" (Do dai: ");
            apb_uart_send_dec(str_len);
            apb_uart_send_string(" byte)\r\n  * So lan phat  : ");
            apb_uart_send_dec(repeat_cnt);
            apb_uart_send_string(" lan\r\n  * Khoang tre   : ");
            apb_uart_send_dec(delay_val);
            apb_uart_send_string(" ms\r\n");
            apb_uart_send_string("----------------------------------------\r\n");
            apb_uart_send_string("[FPGA] Bat dau phat sang Laptop...\r\n");

            for (int i = 1; i <= repeat_cnt; i++) {
                apb_uart_send_string("  -> [Lan #");
                apb_uart_send_dec(i);
                apb_uart_send_string("/");
                apb_uart_send_dec(repeat_cnt);
                apb_uart_send_string("]: \"");
                apb_uart_send_string(custom_str);
                apb_uart_send_string("\"\r\n");
                delay_ms(delay_val);
            }

            apb_uart_send_string("[FPGA] Hoan tat phat chuoi thanh cong!\r\n");
            apb_uart_send_string("\r\nChon [1-5, q]: ");
        }
        else if (sub_choice == '2') {
            // Cấu hình & phát Byte Hex / Nhị phân tùy chọn
            char byte_buf[64];
            char count_buf[32];

            apb_uart_send_string("\r\n\r\n--- [2] CAU HINH BYTE / MA NHI PHAN MUON PHAT ---\r\n");
            apb_uart_send_string("1. Nhap byte (vd Hex 0xAA, 0xFF hoac Bin 10101010b, mac dinh 0xAA): ");
            apb_uart_flush_rx();
            int b_len = apb_uart_read_line(byte_buf, sizeof(byte_buf));
            uint8_t byte_val = (b_len > 0) ? parse_byte(byte_buf, 0xAA) : 0xAA;

            apb_uart_send_string("2. Nhap so luong byte muon phat [1-50] (mac dinh 10): ");
            apb_uart_flush_rx();
            int c_len = apb_uart_read_line(count_buf, sizeof(count_buf));
            int byte_cnt = (c_len > 0) ? parse_int(count_buf, 10) : 10;
            if (byte_cnt < 1) byte_cnt = 1;
            if (byte_cnt > 50) byte_cnt = 50;

            uint32_t cfg = REG_UART_CFG;
            int data_bits = (int)(cfg & 0x3) + 5;
            if (data_bits == 7) byte_val &= 0x7F;

            apb_uart_send_string("\r\n[+] DA LUU CAU HINH PHAT BYTE:\r\n");
            apb_uart_send_string("  * Gia tri Hex  : 0x");
            apb_uart_send_hex8(byte_val);
            apb_uart_send_string(" (Dec: ");
            apb_uart_send_dec(byte_val);
            apb_uart_send_string(")\r\n  * Dang Binary  : ");
            for (int b = data_bits - 1; b >= 0; b--) {
                apb_uart_send_byte(((byte_val >> b) & 1) ? '1' : '0');
            }
            apb_uart_send_string("b (");
            apb_uart_send_dec(data_bits);
            apb_uart_send_string("-bit)\r\n  * Bit 7 (MSB)  : ");
            if (data_bits == 8) {
                apb_uart_send_byte(((byte_val >> 7) & 1) ? '1' : '0');
                apb_uart_send_string("\r\n");
            } else {
                apb_uart_send_string("DA BI CAT (7-bit)\r\n");
            }
            apb_uart_send_string("  * So luong byte: ");
            apb_uart_send_dec(byte_cnt);
            apb_uart_send_string(" byte\r\n");
            apb_uart_send_string("----------------------------------------\r\n");
            apb_uart_send_string("[FPGA] Bat dau phat sang Laptop...\r\n");

            for (int i = 1; i <= byte_cnt; i++) {
                apb_uart_send_byte(byte_val);
                apb_uart_send_string("  -> Phat byte #");
                apb_uart_send_dec(i);
                apb_uart_send_string("/");
                apb_uart_send_dec(byte_cnt);
                apb_uart_send_string(": Hex=0x");
                apb_uart_send_hex8(byte_val);
                apb_uart_send_string(" (Dec=");
                apb_uart_send_dec(byte_val);
                apb_uart_send_string(")\r\n");
                delay_cycles(2000000); // Khoảng 200ms
            }

            apb_uart_send_string("[FPGA] Hoan tat phat byte thanh cong!\r\n");
            apb_uart_send_string("\r\nChon [1-5, q]: ");
        }
        else if (sub_choice == '3') {
            // Phát 5 gói tin mặc định
            apb_uart_send_string("\r\n\r\n[FPGA] Bat dau phat 5 goi tin SoC kiem tra sang Laptop...\r\n");
            for (int i = 1; i <= 5; i++) {
                apb_uart_send_string("  -> [Goi #");
                apb_uart_send_dec(i);
                apb_uart_send_string("/5]: \"Hello Laptop from FPGA DE2 (Nios V 50MHz)!\" [Packet ID: 0x");
                apb_uart_send_hex8((uint8_t)(0xA0 + i));
                apb_uart_send_string("]\r\n");
                delay_cycles(2500000);
            }
            apb_uart_send_string("[FPGA] Hoan tat phat 5 goi tin thanh cong!\r\n");
            apb_uart_send_string("\r\nChon [1-5, q]: ");
        }
        else if (sub_choice == '4') {
            // Phát luồng Telemetry
            apb_uart_send_string("\r\n\r\n[FPGA] Dang phat luong giam sat dinh ky (Telemetry) sang Laptop...\r\n");
            apb_uart_send_string("[!] Bam phim bat ky hoac 'q' tren Laptop de DUNG phat.\r\n\r\n");

            uint32_t pkt_cnt = 1;
            while (1) {
                uint8_t stop_ch;
                if (apb_uart_receive_byte_nonblocking(&stop_ch)) {
                    apb_uart_send_string("\r\n[FPGA] Nhan lenh dung tu Laptop! Da dung phat luong.\r\n");
                    break;
                }

                apb_uart_send_string("[FPGA TELEMETRY #");
                apb_uart_send_dec(pkt_cnt);
                apb_uart_send_string("] Uptime: ~");
                apb_uart_send_dec(pkt_cnt);
                apb_uart_send_string("s | CPU: Nios V 50MHz | APB Status: 0x");
                apb_uart_send_hex8((uint8_t)REG_UART_STATUS);
                apb_uart_send_string(" | Data: 0x");
                uint8_t val = (uint8_t)(pkt_cnt % 256);
                apb_uart_send_hex8(val);
                apb_uart_send_string(" ('");
                if (val >= 32 && val <= 126) apb_uart_send_byte(val);
                else apb_uart_send_byte('.');
                apb_uart_send_string("')\r\n");

                pkt_cnt++;

                bool stopped = false;
                for (int d = 0; d < 20; d++) {
                    delay_cycles(250000);
                    if (apb_uart_receive_byte_nonblocking(&stop_ch)) {
                        stopped = true;
                        break;
                    }
                }
                if (stopped) {
                    apb_uart_send_string("\r\n[FPGA] Nhan lenh dung tu Laptop! Da dung phat luong.\r\n");
                    break;
                }
            }
            apb_uart_send_string("\r\nChon [1-5, q]: ");
        }
        else if (sub_choice == '5') {
            // Phát bảng mã Ramp 256 byte dạng bảng Hex đẹp mắt
            apb_uart_send_string("\r\n\r\n[FPGA] Dang phat bang ma 256 Byte Hex (0x00 -> 0xFF) sang Laptop...\r\n");
            for (int i = 0; i < 256; i++) {
                if (i % 16 == 0) {
                    apb_uart_send_string("\r\n  0x");
                    apb_uart_send_hex8((uint8_t)i);
                    apb_uart_send_string(": ");
                }
                apb_uart_send_hex8((uint8_t)i);
                apb_uart_send_string(" ");
                delay_cycles(20000);
            }
            while (!apb_uart_is_tx_ready());
            delay_cycles(500000);
            apb_uart_send_string("\r\n\r\n[FPGA] Da phat xong 256 byte Hex Ramp Test sang Laptop!\r\n");
            apb_uart_send_string("Chon [1-5, q]: ");
        }
        else {
            apb_uart_send_string("\r\n[!] Lua chon khong hop le! Vui long chon 1-5 hoac q.\r\nChon [1-5, q]: ");
        }
    }
}

// Xử lý các lệnh giao thức tự động bắt đầu bằng '!'
static bool handle_protocol_cmd(uint8_t first_char) {
    if ((first_char & 0x7Fu) != '!') return false;
    char cmd_line[64];
    int c_idx = 0;
    // Tight loop polling để đọc trọn vẹn chuỗi lệnh mà không bị lỡ byte ở 115200 bps
    for (int k = 0; k < 200000; k++) {
        uint8_t c;
        if (apb_uart_receive_byte_nonblocking(&c)) {
            uint8_t clean_c = c & 0x7Fu;
            if (clean_c == '\r' || clean_c == '\n') {
                if (c_idx > 0) break;
            } else if (c_idx < (int)sizeof(cmd_line) - 1) {
                cmd_line[c_idx++] = (char)clean_c;
            }
            k = 0; // Reset bộ đếm timeout mỗi khi nhận ký tự mới
        }
    }
    cmd_line[c_idx] = '\0';

    if (strcmp(cmd_line, "CFG:8N1") == 0) {
        while (!apb_uart_is_tx_ready());
        REG_UART_CFG = UART_CFG_8N1;
        delay_cycles(100000);
        apb_uart_send_string("!CFG_OK:8N1\r\n");
        return true;
    } else if (strcmp(cmd_line, "CFG:8E1") == 0) {
        while (!apb_uart_is_tx_ready());
        REG_UART_CFG = UART_CFG_8E1;
        delay_cycles(100000);
        apb_uart_send_string("!CFG_OK:8E1\r\n");
        return true;
    } else if (strcmp(cmd_line, "CFG:8O1") == 0) {
        while (!apb_uart_is_tx_ready());
        REG_UART_CFG = UART_CFG_8O1;
        delay_cycles(100000);
        apb_uart_send_string("!CFG_OK:8O1\r\n");
        return true;
    } else if (strcmp(cmd_line, "CFG:7E1") == 0) {
        while (!apb_uart_is_tx_ready());
        REG_UART_CFG = UART_CFG_7E1;
        delay_cycles(100000);
        apb_uart_send_string("!CFG_OK:7E1\r\n");
        return true;
    } else if (strcmp(cmd_line, "CFG:7O1") == 0) {
        while (!apb_uart_is_tx_ready());
        REG_UART_CFG = UART_CFG_7O1;
        delay_cycles(100000);
        apb_uart_send_string("!CFG_OK:7O1\r\n");
        return true;
    } else if (strcmp(cmd_line, "CFG:8N2") == 0) {
        while (!apb_uart_is_tx_ready());
        REG_UART_CFG = UART_CFG_8N2;
        delay_cycles(100000);
        apb_uart_send_string("!CFG_OK:8N2\r\n");
        return true;
    } else if (strncmp(cmd_line, "TX_BYTE:", 8) == 0) {
        uint8_t tx_val = parse_byte(cmd_line + 8, 0xAA);
        while (!apb_uart_is_tx_ready());
        apb_uart_send_byte(tx_val);
        return true;
    } else if (strncmp(cmd_line, "TX_STR:", 7) == 0) {
        while (!apb_uart_is_tx_ready());
        apb_uart_send_string(cmd_line + 7);
        apb_uart_send_string("\r\n");
        return true;
    } else if (strcmp(cmd_line, "GET_CFG") == 0) {
        uint32_t cfg = REG_UART_CFG;
        int d_bits = (int)(cfg & 0x3) + 5;
        int p_en = (int)((cfg >> 3) & 0x1);
        int p_type = (int)((cfg >> 4) & 0x1);
        int s_bits = (int)((cfg >> 2) & 0x1) + 1;
        char p_char = (!p_en) ? 'N' : (p_type ? 'E' : 'O');
        apb_uart_send_string("!CFG_CUR:");
        apb_uart_send_dec(d_bits);
        apb_uart_send_byte((uint8_t)p_char);
        apb_uart_send_dec(s_bits);
        apb_uart_send_string("\r\n");
        return true;
    } else if (strcmp(cmd_line, "PING") == 0) {
        while (!apb_uart_is_tx_ready());
        apb_uart_send_string("!PONG\r\n");
        return true;
    }
    return true;
}

// Chế độ 2: Kiểm tra truyền nhận bit nhị phân (0/1) và Byte Hex (0x00 - 0xFF)
static void mode_binary_test(void) {
    uint32_t cfg = REG_UART_CFG;
    int data_bits = (int)(cfg & 0x3) + 5;
    int stop_bits = (int)((cfg >> 2) & 0x1) + 1;
    int parity_en = (int)((cfg >> 3) & 0x1);
    int parity_type = (int)((cfg >> 4) & 0x1);

    apb_uart_send_string("\r\n========================================\r\n");
    apb_uart_send_string(" [CHE DO TEST BIT NHI PHAN (0/1) & HEX]\r\n");
    apb_uart_send_string(" -> Cau hinh FPGA: ");
    if (data_bits == 8 && !parity_en && stop_bits == 1) apb_uart_send_string("8N1 (8 Data, No Parity, 1 Stop)\r\n");
    else if (data_bits == 8 && !parity_en && stop_bits == 2) apb_uart_send_string("8N2 (8 Data, No Parity, 2 Stop)\r\n");
    else if (data_bits == 8 && parity_en && parity_type) apb_uart_send_string("8E1 (8 Data, Even Parity, 1 Stop)\r\n");
    else if (data_bits == 8 && parity_en && !parity_type) apb_uart_send_string("8O1 (8 Data, Odd Parity, 1 Stop)\r\n");
    else if (data_bits == 7 && parity_en && parity_type) apb_uart_send_string("7E1 (7 Data, Even Parity, 1 Stop)\r\n");
    else if (data_bits == 7 && parity_en && !parity_type) apb_uart_send_string("7O1 (7 Data, Odd Parity, 1 Stop)\r\n");
    else apb_uart_send_string("Tuy chon\r\n");

    apb_uart_send_string(" -> Gui byte nhi phan bat ky (vd: 10101010b, 0xAA, 0xFF, 0x71).\r\n");
    apb_uart_send_string(" -> Lenh thoat: Bam phim ESC hoac Ctrl+C de ve Menu.\r\n");
    apb_uart_send_string("========================================\r\n\r\n");

    while (1) {
        uint8_t byte = apb_uart_receive_byte();

        // 1. Kiểm tra lệnh giao thức tự động bắt đầu bằng '!'
        if (handle_protocol_cmd(byte)) {
            continue;
        }

        // 2. Reset/Flush khi nhận ESC (0x1B), Ctrl+C (0x03), Ctrl+D (0x04)
        uint8_t clean_cmd = byte & 0x7Fu;
        if (clean_cmd == 0x1B || clean_cmd == 0x03 || clean_cmd == 0x04) {
            apb_uart_flush_rx();
            apb_uart_send_string("!READY:RESET\r\n");
            continue;
        }

        // Bỏ qua '\r', '\n'
        if (byte == '\r' || byte == '\n') continue;

        bool par_err = apb_uart_has_parity_error();
        uint32_t cur_cfg = REG_UART_CFG;
        int d_bits = (int)(cur_cfg & 0x3) + 5;
        int p_en = (int)((cur_cfg >> 3) & 0x1);
        int p_type = (int)((cur_cfg >> 4) & 0x1);

        // 3. Kiểm tra xem có phải chuỗi Text burst (nhiều byte liên tiếp) hay không
        char text_buf[128];
        int t_len = 0;
        text_buf[t_len++] = (char)byte;
        bool str_par_err = par_err;

        // Tight loop polling để gom toàn bộ chuỗi text ở tốc độ 115200 bps không bị rớt byte
        for (int k = 0; k < 150000; k++) {
            uint8_t next_c;
            if (apb_uart_receive_byte_nonblocking(&next_c)) {
                if (next_c != '\r' && next_c != '\n') {
                    if (t_len < (int)sizeof(text_buf) - 1) {
                        text_buf[t_len++] = (char)next_c;
                        if (apb_uart_has_parity_error()) str_par_err = true;
                    }
                }
                k = 0; // Reset bộ đếm timeout khi có byte tới
            }
        }
        text_buf[t_len] = '\0';

        if (t_len > 1) {
            // Gửi dòng cấu trúc !RX_STR cho script Python
            apb_uart_send_string("!RX_STR:TEXT=");
            apb_uart_send_string(text_buf);
            apb_uart_send_string(",LEN=");
            apb_uart_send_dec(t_len);
            apb_uart_send_string(",PAR_ERR=");
            apb_uart_send_byte(str_par_err ? '1' : '0');
            apb_uart_send_string("\r\n");
            continue;
        }

        // Nhận 1 Byte đơn: phân tích chi tiết từng bit
        int ones = 0;
        for (int b = 0; b < d_bits; b++) {
            if ((byte >> b) & 1) ones++;
        }

        int exp_parity = p_type ? ((ones % 2 != 0) ? 1 : 0) : ((ones % 2 == 0) ? 1 : 0);
        int act_parity = par_err ? (1 - exp_parity) : exp_parity;

        // Dòng cấu trúc chuẩn !RX_BYTE cho script Python
        apb_uart_send_string("!RX_BYTE:HEX=");
        apb_uart_send_hex8(byte);
        apb_uart_send_string(",BIN=");
        for (int b = d_bits - 1; b >= 0; b--) {
            apb_uart_send_byte(((byte >> b) & 1) ? '1' : '0');
        }
        apb_uart_send_string(",BITS=");
        apb_uart_send_dec(d_bits);
        apb_uart_send_string(",MSB=");
        apb_uart_send_byte((d_bits == 8) ? (((byte >> 7) & 1) ? '1' : '0') : '-');
        apb_uart_send_string(",PAR_MODE=");
        apb_uart_send_string(!p_en ? "NONE" : (p_type ? "EVEN" : "ODD"));
        apb_uart_send_string(",PAR_BIT=");
        if (!p_en) apb_uart_send_string("NONE");
        else apb_uart_send_byte(act_parity ? '1' : '0');
        apb_uart_send_string(",PAR_ERR=");
        apb_uart_send_byte(par_err ? '1' : '0');
        apb_uart_send_string("\r\n");
    }
}

// Chế độ 2: Echo đệm dòng (Line Buffering Echo cho chuỗi văn bản)
static void mode_echo(void) {
    char line_buf[128];
    apb_uart_send_string("\r\n========================================\r\n");
    apb_uart_send_string(" [CHE DO TEST KY TU / CHUOI (TEXT ECHO)]\r\n");
    apb_uart_send_string(" -> Nhap bat ky chuoi ky tu (vd: hello, cls, DE2...). \r\n");
    apb_uart_send_string(" -> Go 'q' roi an Enter de ve Menu chinh.\r\n");
    apb_uart_send_string("========================================\r\n\r\n");

    while (1) {
        apb_uart_send_string("Text_Input> ");
        int len = 0;
        bool has_parity_err = false;

        while (len < (int)sizeof(line_buf) - 1) {
            uint8_t ch = apb_uart_receive_byte();

            if (apb_uart_has_parity_error()) {
                has_parity_err = true;
            }

            if (ch == 0x1B) { // Phim ESC
                line_buf[0] = 'q';
                line_buf[1] = '\0';
                len = 1;
                break;
            }

            if (ch == '\r' || ch == '\n') {
                delay_cycles(20000);
                uint8_t extra;
                apb_uart_receive_byte_nonblocking(&extra);
                break;
            }

            if (ch == '\b' || ch == 0x7F) {
                if (len > 0) {
                    len--;
                    apb_uart_send_string("\b \b");
                }
                continue;
            }

            line_buf[len++] = (char)ch;
            apb_uart_send_byte(ch);
        }
        line_buf[len] = '\0';

        if (len == 0) {
            apb_uart_send_string("\r\n");
            continue;
        }

        if (strcmp(line_buf, "q") == 0 || strcmp(line_buf, "Q") == 0 ||
            strcmp(line_buf, "exit") == 0 || strcmp(line_buf, "quit") == 0) {
            apb_uart_send_string("\r\n[THOAT] Quay ve Menu chinh!\r\n");
            print_banner();
            break;
        }

        apb_uart_send_string("\r\n[FPGA PHAN HOI]: \"");
        apb_uart_send_string(line_buf);
        apb_uart_send_string("\" (Do dai: ");
        apb_uart_send_dec(len);
        apb_uart_send_string(" byte | Hex: ");
        for (int i = 0; i < len; i++) {
            apb_uart_send_hex8((uint8_t)line_buf[i]);
            apb_uart_send_string(" ");
        }
        apb_uart_send_string(")\r\n");
        if (has_parity_err) {
            apb_uart_send_string("  [CANH BAO: Phat hien Loi Parity tren duong truyen!]\r\n");
        } else {
            uint32_t cfg = REG_UART_CFG;
            if ((cfg >> 3) & 1) {
                apb_uart_send_string("  [Parity Check: OK - Tat ca cac byte deu dung Parity]\r\n");
            }
        }
        apb_uart_send_string("----------------------------------------\r\n");
    }
}

// Chế độ 3: Đọc trạng thái thanh ghi
static void mode_check_status(void) {
    uint32_t status = apb_uart_get_status();
    uint32_t cfg = REG_UART_CFG;

    apb_uart_send_string("\r\n--- TRANG THAI PHAN CUNG APB UART ---\r\n");
    apb_uart_send_string("  Base Address : 0x");
    apb_uart_send_hex32((uint32_t)APB_UART_BASE);
    apb_uart_send_string("\r\n  CFG  (0x008) : 0x");
    apb_uart_send_hex32(cfg);
    apb_uart_send_string(" (DataBits=");
    apb_uart_send_dec((int32_t)(cfg & 0x3) + 5);
    apb_uart_send_string(", StopBits=");
    apb_uart_send_dec((int32_t)((cfg >> 2) & 0x1) + 1);
    apb_uart_send_string(", ParityEn=");
    apb_uart_send_dec((int32_t)((cfg >> 3) & 0x1));
    apb_uart_send_string(")\r\n  STATUS (0x010): 0x");
    apb_uart_send_hex32(status);
    apb_uart_send_string(" (TX_DONE=");
    apb_uart_send_dec((int32_t)(status & 1));
    apb_uart_send_string(", RX_DONE=");
    apb_uart_send_dec((int32_t)((status >> 1) & 1));
    apb_uart_send_string(", PAR_ERR=");
    apb_uart_send_dec((int32_t)((status >> 2) & 1));
    apb_uart_send_string(")\r\n-------------------------------------\r\n");
}

// Chế độ 4: Thay đổi cấu hình khung truyền UART
static void mode_change_config(void) {
    apb_uart_send_string("\r\n========================================\r\n");
    apb_uart_send_string(" [CAU HINH KHUNG TRUYEN UART]\r\n");
    apb_uart_send_string("   [1] 8N1 (Mac dinh)\r\n");
    apb_uart_send_string("   [2] 8E1 (Even Parity)\r\n");
    apb_uart_send_string("   [3] 8O1 (Odd Parity)\r\n");
    apb_uart_send_string("   [4] 7E1 (Even Parity)\r\n");
    apb_uart_send_string("   [5] 7O1 (Odd Parity)\r\n");
    apb_uart_send_string("   [6] 8N2 (2 Stop bits)\r\n");
    apb_uart_send_string("   [q] Quay ve Menu\r\n");
    apb_uart_send_string("========================================\r\n");
    apb_uart_send_string("Chon [1-6, q]: ");

    uint8_t sel;
    do {
        sel = apb_uart_receive_byte();
    } while (sel == '\r' || sel == '\n');

    uint32_t new_cfg = 0;
    const char *cfg_name = "";

    switch (sel) {
        case '1': new_cfg = UART_CFG_8N1; cfg_name = "8N1"; break;
        case '2': new_cfg = UART_CFG_8E1; cfg_name = "8E1"; break;
        case '3': new_cfg = UART_CFG_8O1; cfg_name = "8O1"; break;
        case '4': new_cfg = UART_CFG_7E1; cfg_name = "7E1"; break;
        case '5': new_cfg = UART_CFG_7O1; cfg_name = "7O1"; break;
        case '6': new_cfg = UART_CFG_8N2; cfg_name = "8N2"; break;
        case 'q':
        case 'Q':
        case 0x1B:
            apb_uart_send_string("\r\n[HUY] Giu nguyen cau hinh cu.\r\n");
            print_banner();
            return;
        default:
            apb_uart_send_string("\r\nLua chon khong hop le!\r\n");
            print_banner();
            return;
    }

    // Chờ ký tự cũ truyền xong hoàn toàn
    while (!apb_uart_is_tx_ready());
    delay_cycles(200000);

    REG_UART_CFG = new_cfg;
    delay_cycles(200000);

    apb_uart_send_string("\r\n[+] Da chuyen sang: ");
    apb_uart_send_string(cfg_name);
    apb_uart_send_string(" (0x");
    apb_uart_send_hex8((uint8_t)new_cfg);
    apb_uart_send_string(")\r\n");

    print_banner();
}

int main(void) {
    // 1. Khoi tao phan cung APB UART: 8N1
    apb_uart_init(UART_CFG_8N1);
    delay_cycles(500000);

    // 2. Gui thong bao san sang khoi dong he thong
    apb_uart_send_string("!READY:8N1\r\n");

    // 3. Vao truc tiep che do xu ly truyen nhan du lieu va lenh giao thuc Nios V
    mode_binary_test();

    return 0;
}
