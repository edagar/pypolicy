from pathlib import Path
import pytest
from lark import Lark

from codegen import CodeGen
from vm import Interpreter


GRAMMAR = Path("policy.lark").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def parser():
    return Lark(GRAMMAR, parser="earley", lexer="dynamic", start="start")


def compile_source(src: str, parser: Lark):
    if not src.endswith("\n"):
        src += "\n"
    tree = parser.parse(src)
    cg = CodeGen()
    bc = cg.compile(tree)
    return tree, bc


@pytest.fixture
def eval_policy(parser):
    """
    eval_policy(src, *, trace=False) -> (interp, bytecode)
    Executes 'src' and returns the Interpreter and bytecode.
    Capture printed output in tests via pytest 'capsys'.
    """
    def _run(src: str, *, trace: bool = False):
        ast, bc = compile_source(src, parser)
        interp = Interpreter()
        if trace:
            interp.set_trace(lambda pc,op,arg,stack: print(f"[pc={pc}] {op} {arg} | stack={stack}"))
        ret = interp.exec(bc)
        return interp, ast, bc, ret
    return _run

