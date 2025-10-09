#! /usr/bin/env python3


from lark import Lark
from codegen import CodeGen
from vm import Interpreter, iPyObject, iPyfunction, iInteger, Opcode
from readonly import freeze


GRAMMAR = open("policy.lark", "r", encoding="utf-8").read()
PARSER = Lark(GRAMMAR, parser="earley", lexer="dynamic", start="start")


def tracer(pc, op, arg, stack):
    print(f"[pc={pc}] {op}, {arg} | stack={stack}")


def main():
    interp = Interpreter()
    token = {"roles": {"my_client": ["admin", "driver"]}}
    interp.store_global("token", iPyObject(token))

    tracing = False
    print("pp REPL. Commands: :q (quit), :trace (toggle), :globals, :stack\n")

    while True:
        try:
            src = input("pp > ").strip()
        except UnicodeDecodeError:
            continue
        except (EOFError, KeyboardInterrupt):
            break
        if not src: continue
        if src in (":q", ":quit"): break
        if src == ":trace":
            tracing = not tracing
            interp.set_trace_hook(tracer if tracing else None)
            print(f"trace = {tracing}")
            continue
        if src == ":globals":
            for k,v in interp.globals.items(): print(f"{k} => {v}")
            continue
        if src == ":stack":
            print(interp.stack)
            continue

        tree = PARSER.parse(src if src.endswith("\n") else src + "\n")
        bc = CodeGen().compile(tree)
        # hack to make sure result is still on the stack so repl can display it
        if bc[-1][0] == Opcode.POP: bc.pop() 
        interp.exec(bc)
        if interp.stack:
            print(interp.pop())


if __name__ == "__main__":
    main()

