all: toggle.hex

%.hex: %.asm
	boneless-as $< -o $@
