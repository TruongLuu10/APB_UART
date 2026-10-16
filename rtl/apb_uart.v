module apb_uart #(
  parameter integer FCLK     = 50000000,    // TAN SO XUNG NHIP HE THONG
  parameter integer BAUDRATE = 115200,      // BAUDRATE mac dinh
  parameter integer OS_TX    = 1,           // Hệ số oversampling cho TX
  parameter integer OS_RX    = 16           // Hệ số oversampling cho RX
) (
  // 1. CHÂN GIAO TIẾP VỚI BO MẠCH FPGA (TOP-LEVEL PINS)
  input  wire        clk,         // Xung nhịp hệ thống (vd: CLOCK_50)
  input  wire        reset_n,     // Nút nhấn Reset (vd: KEY[0] - active low)

  // 2. CHÂN GIAO TIẾP VẬT LÝ NGOẠI VI (UART PINS)
  input  wire        rx,          // Chân nhận dữ liệu nối tiếp từ PC
  input  wire        cts_n,       // Clear-to-send 
  output wire        tx,          // Chân truyền dữ liệu nối tiếp ra PC
  output wire        rts_n        // Request-to-send 
);

  // =====================================================================
  // I. KHAI BÁO CÁC DÂY DẪN TRUNG GIAN (INTERNAL WIRES)
  // =====================================================================

  // 1. Dây dẫn nội bộ cho Bus APB (Nối giữa Nios V và Interface)
  wire [11:0] paddr;
  wire        penable;
  wire        pwrite;
  wire [31:0] pwdata;
  wire [31:0] prdata;
  wire        pready;
  wire        psel;
  wire        pslverr;
  wire [3:0]  pstrb;

  // 2. Dây trung gian điều khiển UART nội bộ
  wire [7:0] tx_data;             
  wire       start_tx;            
  wire       tx_done;             
  wire [7:0] rx_data;             
  wire       rx_done;             
  wire       parity_error;        
  wire       clear_rx_done;       

  // 3. Khung truyền và Baudrate
  wire [1:0] data_bit_num;        
  wire       stop_bit_num;        
  wire       parity_en;           
  wire       parity_type;         
  wire       tx_tick_last;        
  wire       rx_tick_last;        

  // =====================================================================
  // II. GỌI CÁC KHỐI HOẠT ĐỘNG (INSTANTIATIONS)
  // =====================================================================

  // 0. NHÚNG HỆ THỐNG VI XỬ LÝ NIOS V (Khối sinh ra từ Qsys)
  system u_system (
    .clk_clk         (clk),            // Cấp xung nhịp hệ thống
    .reset_reset_n   (reset_n),        // Cấp reset hệ thống
    
    // Nối ngõ ra APB Master vào các dây trung gian
    .apb_bus_paddr   (paddr),   
    .apb_bus_penable (penable), 
    .apb_bus_prdata  (prdata),  
    .apb_bus_pready  (pready),  
    .apb_bus_psel    (psel),    
    .apb_bus_pslverr (pslverr), 
    .apb_bus_pstrb   (pstrb),   
    .apb_bus_pwdata  (pwdata),  
    .apb_bus_pwrite  (pwrite)   
  );

  // 1. Khối APB Slave Interface (Giao tiếp nhận lệnh từ Nios V)
  top_interface_uart_slave apb_interface (
    // Nhận bus APB từ dây trung gian (Nối chung Clock/Reset của hệ thống)
    .pclk          (clk),
    .presetn       (reset_n),
    .psel          (psel),
    .penable       (penable),
    .pwrite        (pwrite),
    .paddr         (paddr),
    .pwdata        (pwdata),
    .pstrb         (pstrb),
    .prdata        (prdata),
    .pready        (pready),
    .pslverr       (pslverr),

    // Giao tiếp TX & RX
    .tx_data       (tx_data),
    .start_tx      (start_tx),
    .tx_done       (tx_done),
    .rx_data       (rx_data),
    .rx_done       (rx_done),
    .parity_error  (parity_error),
    .clear_rx_done (clear_rx_done),

    // Cấu hình khung truyền
    .data_bit_num  (data_bit_num),
    .stop_bit_num  (stop_bit_num),
    .parity_en     (parity_en),
    .parity_type   (parity_type)
  );

  // 2. Khối Sinh Baudrate Dung Chung
  uart_baudrate #(
    .FCLK         (FCLK),
    .BAUDRATE     (BAUDRATE),
    .OS_TX        (OS_TX),
    .OS_RX        (OS_RX)
  ) u_baudrate (
    .clk          (clk),
    .rst_n        (reset_n),
    .tx_tick_last (tx_tick_last),
    .rx_tick_last (rx_tick_last)
  );

  // 3. Khối Truyền UART (Transmitter)
  uart_tx #(
    .DATA_NUM     (8)
  ) u_uart_tx (
    .clk          (clk),
    .rst_n        (reset_n),
    .tx_tick_last (tx_tick_last),
    .start_tx     (start_tx),
    .tx_data      (tx_data),
    .data_bit_num (data_bit_num),
    .stop_bit_num (stop_bit_num),
    .parity_en    (parity_en),
    .parity_type  (parity_type),
    .tx           (tx),
    .tx_done      (tx_done)
  );

  // 4. Khối Nhận UART (Receiver)
  uart_rx u_uart_rx (
    .clk           (clk),
    .rst_n         (reset_n),
    .rx_tick_last  (rx_tick_last),
    .rx            (rx),
    .data_bit_num  (data_bit_num),
    .stop_bit_num  (stop_bit_num),
    .parity_en     (parity_en),
    .parity_type   (parity_type),
    .clear_rx_done (clear_rx_done),
    .rx_data       (rx_data),
    .rx_done       (rx_done),
    .parity_error  (parity_error)
  );

  // Mặc định luôn cho phép nhận (Ready to Receive)
  assign rts_n = 1'b0;

endmodule