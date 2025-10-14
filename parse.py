from lark import Lark
from codegen import CodeGen
from vm import Opcode, iObject, Instruction

from typing import List


GRAMMAR = open("policy.lark", "r", encoding="utf-8").read()
PARSER = Lark(GRAMMAR, parser="earley", lexer="dynamic", start="start")


def compile_source(src: str) -> List[Instruction]:
    return CodeGen().compile(parse_source(src))


def compile_ast(ast) -> List[Instruction]:
    return CodeGen().compile(ast)


def parse_source(src: str):
    return PARSER.parse(src)
