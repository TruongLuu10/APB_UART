#ifndef APB_UART_H_
#define APB_UART_H_

#include <stdint.h>
#include <stdbool.h>
#include "apb_uart_regs.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Khởi tạo ngoại vi APB UART với cấu hình khung truyền mong muốn
 * @param config Tổ hợp các bit cấu hình (ví dụ: UART_CFG_8N1)
 */
void apb_uart_init(uint32_t config);

/**
 * @brief Kiểm tra xem bộ phát (Transmitter) đã sẵn sàng nhận byte mới chưa
 * @return true nếu TX rảnh (tx_done == 1), false nếu đang bận gửi
 */
bool apb_uart_is_tx_ready(void);

/**
 * @brief Kiểm tra xem đã nhận được byte dữ liệu mới từ PC chưa
 * @return true nếu có dữ liệu mới (rx_done == 1), false nếu chưa có
 */
bool apb_uart_has_rx_data(void);

/**
 * @brief Kiểm tra cờ lỗi Parity của byte vừa nhận
 * @return true nếu có lỗi Parity
 */
bool apb_uart_has_parity_error(void);

/**
 * @brief Đọc giá trị thanh ghi trạng thái (stt_reg)
 */
uint32_t apb_uart_get_status(void);

/**
 * @brief Gửi một byte dữ liệu ra PC qua UART (chế độ chặn - blocking)
 *        Hàm sẽ chờ cho đến khi bộ truyền rảnh rồi mới gửi.
 * @param byte Ký tự/byte cần gửi
 */
void apb_uart_send_byte(uint8_t byte);

/**
 * @brief Gửi một chuỗi ký tự kết thúc bằng '\0' ra PC qua UART
 * @param str Chuỗi ký tự cần gửi
 */
void apb_uart_send_string(const char *str);

/**
 * @brief Nhận một byte từ PC qua UART (chế độ chặn - blocking)
 *        Hàm sẽ chờ vô hạn cho đến khi có dữ liệu tới.
 * @return Byte dữ liệu nhận được
 */
uint8_t apb_uart_receive_byte(void);

/**
 * @brief Nhận một byte từ PC qua UART (chế độ không chặn - non-blocking)
 * @param byte Con trỏ lưu byte nhận được nếu có
 * @return true nếu đã nhận được byte thành công, false nếu chưa có dữ liệu
 */
bool apb_uart_receive_byte_nonblocking(uint8_t *byte);

/**
 * @brief Nhận một chuỗi ký tự (dòng văn bản) từ PC cho đến khi gặp ký tự xuống dòng '\r' hoặc '\n'
 * @param buf Bộ đệm lưu chuỗi nhận được
 * @param max_len Kích thước tối đa của bộ đệm (bao gồm cả ký tự kết thúc '\0')
 * @return Số lượng ký tự đã nhận
 */
int apb_uart_read_line(char *buf, int max_len);

/**
 * @brief Gửi số nguyên thập phân (tránh phụ thuộc thư viện libc nặng)
 */
void apb_uart_send_dec(int32_t val);

/**
 * @brief Gửi số Hex 8-bit (2 ký tự hexa, ví dụ: 2A)
 */
void apb_uart_send_hex8(uint8_t val);

/**
 * @brief Gửi số Hex 32-bit (8 ký tự hexa, ví dụ: 00022000)
 */
void apb_uart_send_hex32(uint32_t val);

#ifdef __cplusplus
}
#endif

#endif // APB_UART_H_
