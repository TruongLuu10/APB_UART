package require -exact qsys 14.0

# 1. Tạo system mới tên là system
create_system system
set_project_property DEVICE_FAMILY "Cyclone IV E"
set_project_property DEVICE EP4CE115F29C7

# 2. Thêm các instance IP
# 2.1 Clock Source 50MHz
add_instance clk_0 clock_source
set_instance_parameter_value clk_0 {clockFrequency} {50000000.0}
set_instance_parameter_value clk_0 {resetSynchronousEdges} {NONE}

# 2.2 On-Chip Memory (RAM 40KB)
add_instance on_chip_mem altera_avalon_onchip_memory2
set_instance_parameter_value on_chip_mem {dataWidth} {32}
set_instance_parameter_value on_chip_mem {memorySize} {40960.0}

# 2.3 JTAG UART
add_instance jtag_uart altera_avalon_jtag_uart

# 2.4 Avalon to APB Bridge
add_instance avalon_to_apb_bridge avalon_to_apb_bridge

# 2.5 CPU Nios V/m
add_instance cpu intel_niosv_m
set_instance_parameter_value cpu {enableDebug} {0}
set_instance_parameter_value cpu {resetSlave} {on_chip_mem.s1}
set_instance_parameter_value cpu {resetOffset} {0}

# 3. Kết nối xung nhịp (Clock)
add_connection clk_0.clk cpu.clk
add_connection clk_0.clk on_chip_mem.clk1
add_connection clk_0.clk jtag_uart.clk
add_connection clk_0.clk avalon_to_apb_bridge.clock

# 4. Kết nối Reset
add_connection clk_0.clk_reset cpu.reset
add_connection clk_0.clk_reset on_chip_mem.reset1
add_connection clk_0.clk_reset jtag_uart.reset
add_connection clk_0.clk_reset avalon_to_apb_bridge.reset

# 5. Kết nối Bus Avalon Master / Manager
# Instruction Manager -> On-chip Memory
add_connection cpu.instruction_manager on_chip_mem.s1

# Data Manager -> On-chip Memory, Timer, JTAG UART, Avalon to APB Bridge
add_connection cpu.data_manager on_chip_mem.s1
add_connection cpu.data_manager cpu.timer_sw_agent
add_connection cpu.data_manager jtag_uart.avalon_jtag_slave
add_connection cpu.data_manager avalon_to_apb_bridge.avalon_slave

# 6. Kết nối ngắt (Interrupt)
add_connection cpu.platform_irq_rx jtag_uart.irq
set_connection_parameter_value cpu.platform_irq_rx/jtag_uart.irq irqNumber 0

# 7. Phân bổ địa chỉ (Base Address)
set_connection_parameter_value cpu.instruction_manager/on_chip_mem.s1 baseAddress 0x00000000
set_connection_parameter_value cpu.data_manager/on_chip_mem.s1 baseAddress 0x00000000
set_connection_parameter_value cpu.data_manager/cpu.timer_sw_agent baseAddress 0x00020000
set_connection_parameter_value cpu.data_manager/jtag_uart.avalon_jtag_slave baseAddress 0x00021000
set_connection_parameter_value cpu.data_manager/avalon_to_apb_bridge.avalon_slave baseAddress 0x00022000

# 8. Export các cổng ra ngoài Top Level
# Clock & Reset vào hệ thống
add_interface clk clock sink
set_interface_property clk EXPORT_OF clk_0.clk_in

add_interface reset reset sink
set_interface_property reset EXPORT_OF clk_0.clk_in_reset

# Conduit APB Bus ra module UART
add_interface apb_bus conduit end
set_interface_property apb_bus EXPORT_OF avalon_to_apb_bridge.apb_bus

# 9. Lưu hệ thống vào file system.qsys
save_system system.qsys
send_message info "SYSTEM_GENERATED_SUCCESSFULLY!"
