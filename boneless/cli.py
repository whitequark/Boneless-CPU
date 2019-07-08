import sys
import argparse

from .arch.asm_v3 import TranslationError
from .arch.opcode_v3 import Instr


def as_options(parser):
    parser.add_argument("input",
        metavar="INPUT", type=argparse.FileType("r"),
        help="read assembly from INPUT")
    parser.add_argument("-o", "--output",
        metavar="OUTPUT", type=argparse.FileType("w"),
        help="write machine code (hex) to OUTPUT")
    return parser

def as_main(args=None):
    if args is None:
        args = as_options(argparse.ArgumentParser()).parse_args()

    input  = args.input.read()
    output = args.output or sys.stdout
    try:
        for word in Instr.assemble(input):
            output.write("{:04x}\n".format(word))
    except TranslationError as error:
        print(f"Error: {error}", file=sys.stderr)
        exit(1)


def dis_options(parser):
    parser.add_argument("input",
        metavar="INPUT", type=argparse.FileType("r"),
        help="read machine code (hex) from INPUT")
    parser.add_argument("-o", "--output",
        metavar="OUTPUT", type=argparse.FileType("w"),
        help="write assembly to OUTPUT")
    parser.add_argument("-l", "--labels",
        default=False, action="store_true",
        help="infer labels from PC-relative immediate operands")
    return parser

def dis_main(args=None):
    if args is None:
        args = dis_options(argparse.ArgumentParser()).parse_args()

    input  = []
    for line, word in enumerate(args.input.read().splitlines()):
        try:
            input.append(int(word, 16))
        except ValueError:
            print(f"Error: Invalid hex file at line {line+1}", file=sys.stderr)
            exit(1)
    output = args.output or sys.stdout
    output.write(Instr.disassemble(input, as_text=True, labels=args.labels))


tools  = [
    ("as",  as_options,  as_main),
    ("dis", dis_options, dis_main),
]

def main():
    parser = argparse.ArgumentParser()
    p_tool = parser.add_subparsers(dest="tool", required=True)
    for tool_name, tool_options, tool_main in tools:
        tool_options(p_tool.add_parser(tool_name))
    args = parser.parse_args()
    for tool_name, tool_options, tool_main in tools:
        if args.tool == tool_name:
            tool_main(args)

if __name__ == "__main__":
    main()
