from pathlib import Path
import pytest
from lark import Lark

from pypolicy.codegen import CodeGen
from pypolicy.vm import Interpreter
from pypolicy.parse import compile_source, parse_source, compile_ast



@pytest.fixture
def eval_policy():
    """
    eval_policy(src, *, trace=False) -> (interp, bytecode)
    Executes 'src' and returns the Interpreter and bytecode.
    Capture printed output in tests via pytest 'capsys'.
    """
    def _run(src: str, *, trace: bool = False):
        ast = parse_source(src)
        bc = compile_ast(ast)
        interp = Interpreter()
        if trace:
            interp.set_trace(lambda pc,op,arg,stack: print(f"[pc={pc}] {op} {arg} | stack={stack}"))
        ret = interp.exec(bc)
        return interp, ast, bc, ret
    return _run

