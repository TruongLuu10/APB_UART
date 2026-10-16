# Clock constraints
create_clock -name clk -period 20.000 [get_ports clk]

# Automatically calculate clock uncertainty
derive_clock_uncertainty

# Set false path for reset and asynchronous UART I/O pins
set_false_path -from [get_ports reset_n]
set_false_path -from [get_ports rx]
set_false_path -to [get_ports tx]
