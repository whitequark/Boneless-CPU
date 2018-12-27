#!/bin/sh -e

cd $(dirname $0)
python3 -m boneless.gateware.core_fsm formal generate fsm_core_fi.v
sby -f -d workdir fsm_formal.sby
