cmake_minimum_required(VERSION 3.14)

add_subdirectory(../bsp bsp)

include(../bsp/toolchain.cmake)

project(apb_uart)

enable_language(ASM)
enable_language(C)
enable_language(CXX)

add_executable(apb_uart.elf)

target_sources(apb_uart.elf
    PRIVATE
        ../main.c
        ../apb_uart.c
)

target_include_directories(apb_uart.elf
    PRIVATE
        ..
    PUBLIC
)

target_link_libraries(apb_uart.elf
    PRIVATE
        -T "${BspLinkerScript}" -nostdlib
        "${ExtraArchiveLibraries}"
        -Wl,--start-group "${BspLibraryName}" -lc -lstdc++ -lgcc -lm -Wl,--end-group
)

# Create objdump from ELF.
set(objdump apb_uart.elf.objdump)
add_custom_command(
    OUTPUT "${objdump}"
    DEPENDS apb_uart.elf
    COMMAND "${ToolchainObjdump}" "${ToolchainObjdumpFlags}" apb_uart.elf >
            "${objdump}"
    COMMENT "Creating ${objdump}."
    VERBATIM
)
add_custom_target(create-objdump ALL DEPENDS "${objdump}")

# Report space free for stack + heap. Note that the file below is never created
# so the report is always output on build.
set(stack_report_file apb_uart.elf.stack_report)
add_custom_command(
    OUTPUT "${stack_report_file}"
    DEPENDS apb_uart.elf
    COMMAND niosv-stack-report -p "${ToolchainPrefix}" apb_uart.elf
    COMMENT "Reporting memory available for stack + heap in apb_uart.elf."
    VERBATIM
)
add_custom_target(niosv-stack-report ALL DEPENDS "${stack_report_file}")

# Generate HEX file(s) from apb_uart.elf using elf2hex tool.
# Note : If ECC Full is enabled, width of 39 is set for NiosV TCM. Otherwise, 32.
add_custom_command(
    OUTPUT "on_chip_mem.hex"
    DEPENDS apb_uart.elf
    COMMAND elf2hex apb_uart.elf -o on_chip_mem.hex -b 0x00000000 -w 32 -e 0x00009FFF -r 4
    COMMENT "Creating on_chip_mem.hex."
    VERBATIM
)
add_custom_target(create-hex ALL DEPENDS "on_chip_mem.hex")
