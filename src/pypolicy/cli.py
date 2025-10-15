#! /usr/bin/env python3


from .vm import Interpreter, iPyObject, iPyfunction, iInteger, iString
from .parse import parse_source, compile_ast

import argparse
import sys


def run(bytecode):
    return interp.exec(bytecode)


def default_tracer(pc, op, arg, stack):
    print(f"[pc={pc}] {op}, {arg} | stack={stack}")


def set_default_tracer():
    interp.set_trace_hook(default_tracer)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "-a",
        "--ast-only",
        action="store_true",
        default=False,
        help="Parse source code and display syntax tree without running it"
    )
    argparser.add_argument(
        "-b",
        "--bytecode-only",
        action="store_true",
        default=False,
        help="Compile source code and display bytecode without running it"
    )
    argparser.add_argument("file_path", type=str)
    args = argparser.parse_args()

    interp = Interpreter()
    interp.store_global("set_default_tracer", iPyfunction(set_default_tracer, iInteger(0)))
    token = {"roles": {"my_client": ["admin", "driver"]}}
    interp.store_global("token", iPyObject(token))

    if not args.file_path:
        raise RuntimeError("input file cannot be omitted")

    with open(args.file_path, "r") as fd:
        ast = parse_source(fd.read())

    if args.ast_only:
        print(ast.pretty())
        sys.exit(1)

    bytecode = compile_ast(ast)

    if args.bytecode_only:
        for opcode, arg in bytecode:
            print(opcode, arg)
        sys.exit(1)

    result = run(bytecode)
    print(f"policy return: {result}")

