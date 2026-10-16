#ifndef APB_UART_REGS_H_
#define APB_UART_REGS_H_

#include <stdint.h>

#ifdef __has_include
  #if __has_include("system.h")
    #include "system.h"
  #endif
#endif

// Base address của khối Avalon-to-APB Bridge kết nối tới APB UART
#ifndef APB_UART_BASE
  #ifdef AVALON_TO_APB_BRIDGE_BASE
    #define APB_UART_BASE AVALON_TO_APB_BRIDGE_BASE
  #else
    #define APB_UART_BASE 0x00022000u
  #endif
#endif

// -------------------------------------------------------------
// Offset các thanh ghi của APB UART
// -------------------------------------------------------------
#define APB_UART_TX_DATA_OFFSET   0x0000u  // [W]  Ghi dữ liệu truyền (8-bit)
#define APB_UART_RX_DATA_OFFSET   0x0004u  // [R]  Đọc dữ liệu nhận (tự động clear cờ rx_done)
#define APB_UART_CFG_OFFSET       0x0008u  // [RW] Cấu hình khung truyền (data bit, stop bit, parity)
#define APB_UART_CTRL_OFFSET      0x000Cu  // [W]  Thanh ghi điều khiển (start_tx)
#define APB_UART_STATUS_OFFSET    0x0010u  // [R]  Thanh ghi trạng thái (tx_done, rx_done, parity_error)

// Macro truy cập trực tiếp thanh ghi thông qua con trỏ volatile (chuẩn ANSI C)
#define APB_UART_REG(offset)  (*(volatile uint32_t *)((uintptr_t)(APB_UART_BASE + (offset))))

#define REG_UART_TX_DATA      APB_UART_REG(APB_UART_TX_DATA_OFFSET)
#define REG_UART_RX_DATA      APB_UART_REG(APB_UART_RX_DATA_OFFSET)
#define REG_UART_CFG          APB_UART_REG(APB_UART_CFG_OFFSET)
#define REG_UART_CTRL         APB_UART_REG(APB_UART_CTRL_OFFSET)
#define REG_UART_STATUS       APB_UART_REG(APB_UART_STATUS_OFFSET)

// -------------------------------------------------------------
// Định nghĩa Bitmask cho thanh ghi cấu hình (CFG_REG - Offset 0x008)
// -------------------------------------------------------------
// Bit [1:0]: Số bit dữ liệu
#define UART_CFG_DATA_5BIT    (0x0u << 0)
#define UART_CFG_DATA_6BIT    (0x1u << 0)
#define UART_CFG_DATA_7BIT    (0x2u << 0)
#define UART_CFG_DATA_8BIT    (0x3u << 0)

// Bit [2]: Số bit dừng (Stop bit)
#define UART_CFG_STOP_1BIT    (0x0u << 2)
#define UART_CFG_STOP_2BIT    (0x1u << 2)

// Bit [3]: Cho phép Parity (Parity Enable)
#define UART_CFG_PARITY_DIS   (0x0u << 3)
#define UART_CFG_PARITY_EN    (0x1u << 3)

// Bit [4]: Kiểu Parity (0 = Odd, 1 = Even)
#define UART_CFG_PARITY_ODD   (0x0u << 4)
#define UART_CFG_PARITY_EVEN  (0x1u << 4)

// Cac cau hinh khung truyen thong dung
#define UART_CFG_8N1          (UART_CFG_DATA_8BIT | UART_CFG_STOP_1BIT | UART_CFG_PARITY_DIS)                         // 0x03
#define UART_CFG_8E1          (UART_CFG_DATA_8BIT | UART_CFG_STOP_1BIT | UART_CFG_PARITY_EN | UART_CFG_PARITY_EVEN) // 0x1B
#define UART_CFG_8O1          (UART_CFG_DATA_8BIT | UART_CFG_STOP_1BIT | UART_CFG_PARITY_EN | UART_CFG_PARITY_ODD)  // 0x0B
#define UART_CFG_7E1          (UART_CFG_DATA_7BIT | UART_CFG_STOP_1BIT | UART_CFG_PARITY_EN | UART_CFG_PARITY_EVEN) // 0x1A
#define UART_CFG_7O1          (UART_CFG_DATA_7BIT | UART_CFG_STOP_1BIT | UART_CFG_PARITY_EN | UART_CFG_PARITY_ODD)  // 0x0A
#define UART_CFG_7N1          (UART_CFG_DATA_7BIT | UART_CFG_STOP_1BIT | UART_CFG_PARITY_DIS)                         // 0x02
#define UART_CFG_8N2          (UART_CFG_DATA_8BIT | UART_CFG_STOP_2BIT | UART_CFG_PARITY_DIS)                         // 0x07

// -------------------------------------------------------------
// Định nghĩa Bitmask cho thanh ghi điều khiển (CTRL_REG - Offset 0x00C)
// -------------------------------------------------------------
#define UART_CTRL_START_TX    (1u << 0)  // Phát xung bắt đầu gửi dữ liệu

// -------------------------------------------------------------
// Định nghĩa Bitmask cho thanh ghi trạng thái (STATUS_REG - Offset 0x010)
// -------------------------------------------------------------
#define UART_STATUS_TX_DONE   (1u << 0)  // 1: TX rảnh / đã gửi xong, 0: Đang bận gửi
#define UART_STATUS_RX_DONE   (1u << 1)  // 1: Đã nhận được 1 byte mới, 0: Chưa có dữ liệu
#define UART_STATUS_PAR_ERR   (1u << 2)  // 1: Phát hiện lỗi kiểm tra Parity

#endif // APB_UART_REGS_H_
