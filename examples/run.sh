#!/bin/sh -ex

cd $(dirname $0)
python3 -m boneless.gateware.core_fsm pins generate fsm_core_pins.v
yosys fsm_core_pins.v iceblink.sv -p "synth_ice40 -top top -json iceblink.json"
nextpnr-ice40 --hx1k --package vq100 --pcf iceblink.pcf --json iceblink.json --asc iceblink.txt
icepack iceblink.txt iceblink.bin
iCEburn -e -w iceblink.bin
