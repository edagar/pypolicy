from lark import Lark
from codegen import CodeGen
from vm import Interpreter, iFunction, iString, iInteger, iNil, iList


GRAMMAR = open("policy.lark", "r", encoding="utf-8").read()
PARSER = Lark(GRAMMAR, parser="earley", lexer="dynamic", start="start")


def compile_str(src: str):
    tree = PARSER.parse(src if src.endswith("\n") else src + "\n")
    return CodeGen().compile(tree)


def register_dsl_method(
    interp: Interpreter,
    *,
    src: str,
    func_name: str,
    attach_as: str,
    attach_to: type,
) -> None:
    # Compile and execute the DSL function so it exists in globals
    bc = compile_str(src)
    interp.exec(bc)

    # Pull the compiled function object from globals
    fn_obj = interp.globals.get(func_name)
    if not isinstance(fn_obj, iFunction):
        raise RuntimeError(f"DSL function {func_name!r} not found or not an iFunction")

    interp.register_method(attach_to, attach_as, fn_obj)
    del interp.globals[func_name]
