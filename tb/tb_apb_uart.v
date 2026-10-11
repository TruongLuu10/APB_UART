`timescale 1ns/1ps

module tb_apb_uart;

  //-------------------------------------------------------------
  // 1. KHAI BAO TIN HIEU KET NOI VOI TOP APB UART
  //-------------------------------------------------------------
  reg         clk;
  reg         reset_n;
  reg         pclk;
  reg         presetn;

  reg         psel;
  reg         penable;
  reg         pwrite;
  reg  [3:0]  pstrb;
  reg  [11:0] paddr;
  reg  [31:0] pwdata;
  wire        pready;
  wire        pslverr;
  wire [31:0] prdata;

  wire        tx;
  wire        rx;
  reg         cts_n;
  wire        rts_n;

  // Loopback ngoai vi: noi dau ra TX sang dau vao RX
  assign rx = tx;

  integer pass_cnt;
  integer err_cnt;

  //-------------------------------------------------------------
  // 2. KHOI TAO TOP MODULE APB_UART (DUT)
  // Dat FCLK = 10MHz, BAUDRATE = 1MHz (10 clock/bit de mo phong sieu nhanh)
  //-------------------------------------------------------------
  apb_uart #(
    .FCLK     (10000000),
    .BAUDRATE (1000000)
  ) dut (
    .clk      (clk),
    .reset_n  (reset_n),
    .pclk     (pclk),
    .presetn  (presetn),
    .psel     (psel),
    .penable  (penable),
    .pwrite   (pwrite),
    .pstrb    (pstrb),
    .paddr    (paddr),
    .pwdata   (pwdata),
    .pready   (pready),
    .pslverr  (pslverr),
    .prdata   (prdata),
    .rx       (rx),
    .cts_n    (cts_n),
    .tx       (tx),
    .rts_n    (rts_n)
  );

  //-------------------------------------------------------------
  // 3. TAO XUNG CLOCK (Chu ky 20ns = 50MHz, he thong & APB dong bo)
  //-------------------------------------------------------------
  initial begin
    clk = 0;
    pclk = 0;
    forever begin
      #10 clk = ~clk; pclk = ~pclk;
    end
  end

  //-------------------------------------------------------------
  // 4. KICH BAN KIEM THU END-TO-END CHO TOAN BO HE THONG UART
  //-------------------------------------------------------------
  initial begin
    $dumpfile("tb_apb_uart.vcd");
    $dumpvars(0, tb_apb_uart);

    pass_cnt = 0;
    err_cnt  = 0;
    reset_n  = 0;
    presetn  = 0;
    psel     = 0;
    penable  = 0;
    pwrite   = 0;
    pstrb    = 4'b0000;
    paddr    = 12'h000;
    pwdata   = 32'h0;
    cts_n    = 0;

    $display("==========================================================");
    $display("BAT DAU KIEM THU END-TO-END TOAN BO HE THONG APB UART");
    $display("==========================================================");

    // B1: Reset he thong
    #40;
    reset_n = 1;
    presetn = 1;
    @(posedge pclk);

    // Kiem tra gia tri mac dinh stt_reg (0x010) phai co tx_done = 1
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h010;
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (prdata[0] == 1'b1) begin
      $display("[PASS] TC1: Reset he thong thanh cong, tx_done = 1 (stt_reg = 0x%08h)", prdata);
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC1: Reset sai! prdata = 0x%08h", prdata);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0;

    // B2: Cau hinh khung truyen (8 data bits, 1 stop bit, khong parity) -> ghi 0x03 vao cfg_reg (0x008)
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h008; pwdata = 32'h03; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0;
    $display("[INFO] Da cau hinh cfg_reg = 8-bit data, 1 stop bit, no parity");

    // B3: Ghi byte du lieu 8'hA5 vao tx_data_reg (0x000)
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h000; pwdata = 32'hA5; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0;

    // B4: Kich hoat truyen: Ghi 1 vao ctrl_reg (0x00C)
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h00C; pwdata = 32'h01; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0;
    $display("[INFO] Da phat lenh start_tx cho byte 0xA5, du lieu dang duoc truyen noi tiep qua TX -> RX...");

    // B5: Cho TX truyen va RX nhan xong qua Loopback (doc stt_reg polling bit 1 rx_done)
    repeat (200) @(posedge pclk); // Cho khoang 200 clock (1 khung 10 bit chi ton ~100 clock)

    // Doc stt_reg kiem tra rx_done
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h010;
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (prdata[1] == 1'b1) begin
      $display("[PASS] TC2: TX da truyen va RX da nhan xong qua Loopback! rx_done = 1");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC2: Chua nhan duoc du lieu qua Loopback! stt_reg = 0x%08h", prdata);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0;

    // B6: CPU doc rx_data_reg (0x004) de lay du lieu nhan duoc
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h004;
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (prdata[7:0] == 8'hA5) begin
      $display("[PASS] TC3: Du lieu nhan duoc 0x%02h khop 100%% voi du lieu gui di 0xA5!", prdata[7:0]);
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC3: Du lieu nhan duoc sai! Nhan: 0x%02h (Mong muon: 0xA5)", prdata[7:0]);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0;

    // B7: Kiem tra clear_rx_done: Sau khi doc 0x004, co rx_done trong stt_reg phai duoc xoa ve 0
    @(posedge pclk);
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h010;
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (prdata[1] == 1'b0) begin
      $display("[PASS] TC4: Co rx_done da duoc xoa ve 0 thanh cong sau khi CPU doc rx_data_reg!");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC4: Co rx_done chua duoc xoa! stt_reg = 0x%08h", prdata);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0;

    // B8: Truyen tiep byte thu hai 8'h3C voi che do Parity Even de kiem tra toan ven
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h008; pwdata = 32'h1B; pstrb = 4'h1; // 8b, 1 stop, Parity Even
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0;

    // Ghi 8'h3C vao 0x000 va start
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h000; pwdata = 32'h3C; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0;

    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h00C; pwdata = 32'h01; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0;

    repeat (220) @(posedge pclk);

    // Doc rx_data_reg (0x004)
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h004;
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (prdata[7:0] == 8'h3C) begin
      $display("[PASS] TC5: Truyen byte thu hai 0x%02h co Parity Even thanh cong my man!", prdata[7:0]);
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC5: Byte thu hai sai! prdata = 0x%08h", prdata);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0;

    // Tong ket
    $display("\n==========================================================");
    $display("TONG KET KIEM THU END-TO-END HE THONG APB UART:");
    $display("SO TESTCASE THANH CONG: %0d", pass_cnt);
    $display("SO TESTCASE THAT BAI:   %0d", err_cnt);
    if (err_cnt == 0) $display("KET LUAN: >>> HE THONG APB UART HOAT DONG HOAN HAO 100%%! <<<");
    else              $display("KET LUAN: >>> CO LOI TRONG HE THONG! <<<");
    $display("==========================================================");

    #50;
    $finish;
  end

endmodule
