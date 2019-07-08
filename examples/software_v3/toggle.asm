	.word 0
	.word 0
	.word 0
	.word 0
	.word 0
	.word 0
	.word 0
	.word 0
entry:
	XORI	R0, R0, 0x1000
	STXA	R0, 0
	J	entry
