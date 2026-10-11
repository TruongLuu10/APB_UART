`timescale 1ns/1ps

module tb_top_interface_uart_slave;

  //-------------------------------------------------------------
  // 1. TIN HIEU KET NOI VOI DUT (INTERFACE APB SLAVE)
  //-------------------------------------------------------------
  reg         pclk;
  reg         presetn;
  reg         psel;
  reg         penable;
  reg         pwrite;
  reg  [11:0] paddr;
  reg  [31:0] pwdata;
  reg  [3:0]  pstrb;
  wire [31:0] prdata;
  wire        pready;
  wire        pslverr;

  wire [7:0]  tx_data;
  wire        start_tx;
  reg         tx_done;

  reg  [7:0]  rx_data;
  reg         rx_done;
  reg         parity_error;
  wire        clear_rx_done;

  wire [1:0]  data_bit_num;
  wire        stop_bit_num;
  wire        parity_en;
  wire        parity_type;

  integer pass_cnt;
  integer err_cnt;

  //-------------------------------------------------------------
  // 2. KHOI TAO DUT
  //-------------------------------------------------------------
  top_interface_uart_slave dut (
    .pclk          (pclk),
    .presetn       (presetn),
    .psel          (psel),
    .penable       (penable),
    .pwrite        (pwrite),
    .paddr         (paddr),
    .pwdata        (pwdata),
    .pstrb         (pstrb),
    .prdata        (prdata),
    .pready        (pready),
    .pslverr       (pslverr),
    .tx_data       (tx_data),
    .start_tx      (start_tx),
    .tx_done       (tx_done),
    .rx_data       (rx_data),
    .rx_done       (rx_done),
    .parity_error  (parity_error),
    .clear_rx_done (clear_rx_done),
    .data_bit_num  (data_bit_num),
    .stop_bit_num  (stop_bit_num),
    .parity_en     (parity_en),
    .parity_type   (parity_type)
  );

  // Xung clock 50MHz (T = 20ns)
  initial begin
    pclk = 0;
    forever #10 pclk = ~pclk;
  end

  //-------------------------------------------------------------
  // 3. 12 EDGE CASES KIEM THU CHI TIET CHO KHOI INTERFACE
  //-------------------------------------------------------------
  initial begin
    $dumpfile("tb_top_interface_uart_slave.vcd");
    $dumpvars(0, tb_top_interface_uart_slave);

    pass_cnt     = 0;
    err_cnt      = 0;
    presetn      = 0;
    psel         = 0;
    penable      = 0;
    pwrite       = 0;
    paddr        = 12'h0;
    pwdata       = 32'h0;
    pstrb        = 4'h0;
    tx_done      = 1;
    rx_data      = 8'h0;
    rx_done      = 0;
    parity_error = 0;

    $display("==========================================================");
    $display("BAT DAU KIEM THU 12 EDGE CASES KHOI INTERFACE APB SLAVE");
    $display("==========================================================");

    // --- TC1: Reset he thong & Gia tri mac dinh ---
    #25; presetn = 1; @(posedge pclk);
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h010;
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (prdata == 32'h00000001 && pready && !pslverr) begin
      $display("[PASS] TC1: Reset dung, stt_reg = 0x%08h (tx_done = 1)", prdata);
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC1: Reset sai! prdata = 0x%08h", prdata);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0; @(posedge pclk);

    // --- TC2: Ghi va Doc tx_data_reg (0x000) ---
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h000; pwdata = 32'hA5; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0; @(posedge pclk);
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h000;
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (tx_data == 8'hA5 && prdata[7:0] == 8'hA5) begin
      $display("[PASS] TC2: Ghi doc tx_data_reg thanh cong (0xA5)");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC2: Sai tx_data_reg! tx_data = 0x%02h, prdata = 0x%08h", tx_data, prdata);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0; @(posedge pclk);

    // --- TC3: Cau hinh cfg_reg (0x008) ---
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h008; pwdata = 32'h1F; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0; @(posedge pclk);
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h008;
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (data_bit_num == 2'b11 && stop_bit_num && parity_en && parity_type && prdata[4:0] == 5'b11111) begin
      $display("[PASS] TC3: Cau hinh cfg_reg thanh cong (8b, 2 stop, Even)");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC3: Sai cfg_reg! prdata = 0x%08h", prdata);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0; @(posedge pclk);

    // --- TC4: Auto-Clear start_tx trong ctrl_reg (0x00C) ---
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h00C; pwdata = 32'h01; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0;
    @(posedge pclk);
    if (start_tx == 1'b0) begin
      $display("[PASS] TC4: start_tx da tu dong xoa ve 0 sau 1 clock (Auto-Clear)");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC4: start_tx chua ve 0! start_tx = %b", start_tx);
      err_cnt = err_cnt + 1;
    end
    @(posedge pclk);

    // --- TC5: RX nhan du lieu va clear_rx_done khi doc 0x004 ---
    rx_data = 8'h3C; rx_done = 1; parity_error = 1; @(posedge pclk);
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h004;
    @(posedge pclk); penable = 1; #1;
    if (clear_rx_done == 1'b1 && prdata[7:0] == 8'h3C) begin
      $display("[PASS] TC5: Doc rx_data_reg dung (0x3C) va phat xung clear_rx_done = 1");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC5: Loi doc 0x004! prdata = 0x%08h, clear = %b", prdata, clear_rx_done);
      err_cnt = err_cnt + 1;
    end
    @(posedge pclk); psel = 0; penable = 0; rx_done = 0; parity_error = 0; @(posedge pclk);

    // --- TC6: Read-After-Write (Ghi xong doc lai ngay lap tuc) ---
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h000; pwdata = 32'hB4; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h000; // Doc ngay
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (prdata[7:0] == 8'hB4 && tx_data == 8'hB4) begin
      $display("[PASS] TC6: Read-After-Write thanh cong, lay dung 0xB4 ngay lap tuc");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC6: Read-After-Write that bai! prdata = 0x%08h", prdata);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0; @(posedge pclk);

    // --- TC7: Back-to-Back transfers (2 lenh ghi lien tiep khong IDLE) ---
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h000; pwdata = 32'h11; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h000; pwdata = 32'h22; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0; @(posedge pclk);
    if (tx_data == 8'h22) begin
      $display("[PASS] TC7: Back-to-Back thanh cong, tx_data = 0x22");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC7: Loi Back-to-Back! tx_data = 0x%02h", tx_data);
      err_cnt = err_cnt + 1;
    end

    // --- TC8: Stalled SETUP (penable bi tre nhieu chu ky clock) ---
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h000; pwdata = 32'h77; pstrb = 4'h1;
    @(posedge pclk); @(posedge pclk); #1; // Cho them 2 clock
    if (pready == 1'b0) begin
      $display("[PASS] TC8.1: Master giu SETUP, FSM dung cho dung chuan (pready = 0)");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC8.1: FSM tu nhay vao ACCESS som! pready = %b", pready);
      err_cnt = err_cnt + 1;
    end
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0; @(posedge pclk);
    if (tx_data == 8'h77) begin
      $display("[PASS] TC8.2: Sau khi bat penable, ghi thanh cong tx_data = 0x77");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC8.2: Ghi that bai! tx_data = 0x%02h", tx_data);
      err_cnt = err_cnt + 1;
    end

    // --- TC9: Dia chi khong hop le (pslverr) ---
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h100; pwdata = 32'h1234; pstrb = 4'h1;
    @(posedge pclk); penable = 1; #1;
    if (pslverr == 1'b1 && pready == 1'b1) begin
      $display("[PASS] TC9: Bao loi pslverr = 1 khi truy cap dia chi sai 0x100");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC9: Khong bat pslverr! pslverr = %b", pslverr);
      err_cnt = err_cnt + 1;
    end
    @(posedge pclk); psel = 0; penable = 0; @(posedge pclk);

    // --- TC10: Bao ve thanh ghi Read-Only (rx_data_reg 0x004) ---
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h004; pwdata = 32'hFF; pstrb = 4'h1;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0; @(posedge pclk);
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h004;
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (prdata[7:0] == 8'h3C) begin
      $display("[PASS] TC10: Thanh ghi RO (0x004) duoc bao ve, khong bi ghi de rac");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC10: Thanh ghi RO bi ghi de! prdata = 0x%08h", prdata);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0; @(posedge pclk);

    // --- TC11: Byte Strobe pstrb[0] = 0 chan ghi ---
    @(posedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = 12'h000; pwdata = 32'h99; pstrb = 4'h0;
    @(posedge pclk); penable = 1;
    @(posedge pclk); psel = 0; penable = 0; @(posedge pclk);
    if (tx_data == 8'h77) begin
      $display("[PASS] TC11: pstrb[0] = 0 chan ghi dung, du lieu giu nguyen 0x77");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC11: pstrb[0] = 0 nhung van bi ghi de! tx_data = 0x%02h", tx_data);
      err_cnt = err_cnt + 1;
    end

    // --- TC12: Race Condition (RX nhan byte moi dung luc CPU dang doc 0x004) ---
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h004;
    @(posedge pclk); penable = 1; rx_data = 8'h7E; rx_done = 1;
    @(posedge pclk); psel = 0; penable = 0; rx_done = 0; @(posedge pclk);
    @(posedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = 12'h004;
    @(posedge pclk); penable = 1;
    @(posedge pclk);
    if (prdata[7:0] == 8'h7E) begin
      $display("[PASS] TC12: Byte moi 0x7E duoc chot an toan sau Race Condition!");
      pass_cnt = pass_cnt + 1;
    end else begin
      $display("[FAIL] TC12: Mat du lieu trong Race Condition! prdata = 0x%08h", prdata);
      err_cnt = err_cnt + 1;
    end
    psel = 0; penable = 0; @(posedge pclk);

    // --- TONG KET ---
    $display("\n==========================================================");
    $display("TONG KET KIEM THU INTERFACE APB SLAVE:");
    $display("SO TESTCASE THANH CONG: %0d", pass_cnt);
    $display("SO TESTCASE THAT BAI:   %0d", err_cnt);
    if (err_cnt == 0) $display("KET LUAN: >>> INTERFACE APB SLAVE DAT DIEM TOI DA! <<<");
    else              $display("KET LUAN: >>> CO LOI CAN KIEM TRA! <<<");
    $display("==========================================================");

    #50;
    $finish;
  end

endmodule
