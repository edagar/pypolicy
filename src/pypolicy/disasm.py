from typing import Iterable, Tuple
from .vm import Opcode, iObject, iInteger, iString, iBool, iNil


def _arg_str(arg: iObject | None) -> str:
    match arg:
        case None:
            return ""
        case iInteger():
            return f"[iInt] {arg.value()}"
        case iString():
            return f"[iStr] {arg.value()!r}"
        case iBool():
            return f"[iBool] {arg.value()}"
        case iNil():
            return "[iNil]"
    try:
        v = arg.value()
    except Exception:
        v = arg
    return f"[{type(arg).__name__}] {v!r}"


def _jump_target(idx: int, op: Opcode, arg: iObject | None, code_len: int) -> str:
    if arg is None or not isinstance(arg, iInteger):
        return ""
    rel = int(arg.value())
    if op in (Opcode.JUMP, Opcode.JUMP_IF_FALSE):
        tgt = idx + 1 + rel
        if 0 <= tgt < code_len:
            return f" -> @{tgt}"
        return f" -> @{tgt} (out-of-range)"
    return ""


def disassemble(code: Iterable[Tuple[Opcode, iObject | None]]) -> str:
    lines = []
    code_list = list(code)
    n = len(code_list)
    for i, (op, arg) in enumerate(code_list):
        j = _jump_target(i, op, arg, n)
        a = _arg_str(arg)
        if a:
            lines.append(f"{i:04d}: {op.name:<14} {a}{j}")
        else:
            lines.append(f"{i:04d}: {op.name}")
    return "\n".join(lines)


def print_dis(code: Iterable[Tuple[Opcode, iObject | None]]) -> None:
    print(disassemble(code))
