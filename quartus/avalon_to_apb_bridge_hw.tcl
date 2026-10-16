# _hw.tcl for avalon_to_apb_bridge
package require -exact qsys 14.0

# Module properties
set_module_property DESCRIPTION "Avalon-MM to APB Bridge"
set_module_property NAME avalon_to_apb_bridge
set_module_property VERSION 1.0
set_module_property INTERNAL false
set_module_property OPAQUE_ADDRESS_MAP true
set_module_property GROUP "Bridges"
set_module_property DISPLAY_NAME "Avalon-MM to APB Bridge"
set_module_property INSTANTIATE_IN_SYSTEM_MODULE true
set_module_property EDITABLE true
set_module_property REPORT_TO_TALKBACK false
set_module_property ALLOW_GREYBOX_GENERATION false
set_module_property REPORT_HIERARCHY false

# File sets
add_fileset QUARTUS_SYNTH QUARTUS_SYNTH "" ""
set_fileset_property QUARTUS_SYNTH TOP_LEVEL avalon_apb_bridge
set_fileset_property QUARTUS_SYNTH ENABLE_RELATIVE_INCLUDE_PATHS false
set_fileset_property QUARTUS_SYNTH ENABLE_FILE_OVERWRITE_MODE false
add_fileset_file avalon_to_apb_bridge.v VERILOG PATH ../rtl/avalon_to_apb_bridge.v TOP_LEVEL_FILE

add_fileset SIM_VERILOG SIM_VERILOG "" ""
set_fileset_property SIM_VERILOG TOP_LEVEL avalon_apb_bridge
set_fileset_property SIM_VERILOG ENABLE_RELATIVE_INCLUDE_PATHS false
set_fileset_property SIM_VERILOG ENABLE_FILE_OVERWRITE_MODE false
add_fileset_file avalon_to_apb_bridge.v VERILOG PATH ../rtl/avalon_to_apb_bridge.v

# Clock interface
add_interface clock clock end
set_interface_property clock clockRate 0
set_interface_property clock ENABLED true
add_interface_port clock clk clk Input 1

# Reset interface
add_interface reset reset end
set_interface_property reset associatedClock clock
set_interface_property reset synchronousEdges DEASSERT
set_interface_property reset ENABLED true
add_interface_port reset reset_n reset_n Input 1

# Avalon-MM Slave interface
add_interface avalon_slave avalon end
set_interface_property avalon_slave addressUnits SYMBOLS
set_interface_property avalon_slave associatedClock clock
set_interface_property avalon_slave associatedReset reset
set_interface_property avalon_slave bitsPerSymbol 8
set_interface_property avalon_slave burstOnBurstBoundariesOnly false
set_interface_property avalon_slave burstcountUnits WORDS
set_interface_property avalon_slave explicitAddressSpan 0
set_interface_property avalon_slave holdTime 0
set_interface_property avalon_slave linewrapBursts false
set_interface_property avalon_slave maximumPendingReadTransactions 1
set_interface_property avalon_slave maximumPendingWriteTransactions 1
set_interface_property avalon_slave readLatency 0
set_interface_property avalon_slave readWaitStates 0
set_interface_property avalon_slave readWaitTime 0
set_interface_property avalon_slave setupTime 0
set_interface_property avalon_slave timingUnits Cycles
set_interface_property avalon_slave writeWaitTime 0
set_interface_property avalon_slave ENABLED true

add_interface_port avalon_slave av_address address Input 12
add_interface_port avalon_slave av_read read Input 1
add_interface_port avalon_slave av_write write Input 1
add_interface_port avalon_slave av_writedata writedata Input 32
add_interface_port avalon_slave av_byteenable byteenable Input 4
add_interface_port avalon_slave av_waitrequest waitrequest Output 1
add_interface_port avalon_slave av_readdata readdata Output 32
add_interface_port avalon_slave av_readdatavalid readdatavalid Output 1
add_interface_port avalon_slave av_writeresponsevalid writeresponsevalid Output 1
add_interface_port avalon_slave av_response response Output 2

# Conduit interface (APB bus output to external peripheral)
add_interface apb_bus conduit end
set_interface_property apb_bus associatedClock clock
set_interface_property apb_bus associatedReset reset
set_interface_property apb_bus ENABLED true

add_interface_port apb_bus psel psel Output 1
add_interface_port apb_bus penable penable Output 1
add_interface_port apb_bus pwrite pwrite Output 1
add_interface_port apb_bus paddr paddr Output 12
add_interface_port apb_bus pwdata pwdata Output 32
add_interface_port apb_bus pstrb pstrb Output 4
add_interface_port apb_bus pready pready Input 1
add_interface_port apb_bus pslverr pslverr Input 1
add_interface_port apb_bus prdata prdata Input 32
