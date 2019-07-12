# Introduction
# ------------
#
# _Boneless-III_ is a CPU architecture created specifically for FPGA control plane, with the goals
# being minimal FPGA resource (logic and timing) consumption and convenient assembly programming.
# It is not directly derived from any existing CPU architecture, but borrows ideas from cores such
# as 8051, MIPS and AVR.
#
# Overview
# --------
#
# The Boneless architecture provides:
#
#  * Unified 16-bit register, code and data word size; word-addressable only.
#  * Radical von Neumann architecture: registers, code and data share address space; registers
#    are placed into aligned, movable window into main memory.
#  * Flexible immediates; ALU instructions use a compact encoding for common immediate values,
#    and any immediate may be extended to full word size with a prefix; any ALU instruction may
#    be used with an immediate.
#  * Flexible addressing modes for loads, stores and jumps; dedicated instructions for all common
#    indirect operations; all code position-independent by default.
#  * Rich set of conditionals with four flags, Z (zero), S (sign), C (carry), V (overflow);
#    jump conditions include set and clear flag as well as signed and unsigned integer inequality.
#  * Flexible window instructions; 1-operation prolog and epilog for stem and leaf functions;
#    1-operation window-relative spills; 1-operation context switch.
#  * Secondary address space for peripherals with dedicated addressing modes; all 64K of main
#    address space available for code and data.
#  * Extensible opcode space with room for future additions such as `MUL`/`DIV`; one 3-bit prefix
#    permanently reserved for application-specific opcodes.
#
# Design
# ------
#
# See `doc/manual.pdf` and `doc/design.ods`.
#
# Implementation
# --------------
#
# Boneless can be efficiently implemented with a single 16-bit wide single-port block RAM
# primitive, e.g. on iCE40UP5K, this could be one 16Kx16 SPRAM or one 256x16 BRAM.
