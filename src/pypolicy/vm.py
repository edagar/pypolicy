#! /usr/bin/env python3

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Callable


class iType(Enum):
    NUMBER     = "num"
    STRING     = "str"
    BOOL       = "bool"
    FUNCTION   = "func"
    PYFUNCTION = "pyfunc"
    PYOBJECT   = "pyobj"
    LIST       = "list"
    DICT       = "dict"
    NIL        = "nil"
    METHOD     = "method"


class iObject(ABC):

    @abstractmethod
    def type(self) -> iType:
        pass

    @abstractmethod
    def value(self) -> Any:
        pass

    def __repr__(self) -> str:
        return f"[{self.type()}] {self.value()}"

    def __eq__(self, other):
        if isinstance(other, iObject):
            return self.value() == other.value()
        return self.value() == other
    

class iInteger(iObject):
    def __init__(self, val: int):
        self.val = val

    def type(self) -> iType:
        return iType.NUMBER

    def value(self) -> Any:
        return self.val


class iBool(iObject):
    def __init__(self, val: bool):
        self.val = val

    def type(self) -> iType:
        return iType.BOOL

    def value(self) -> Any:
        return self.val


class iString(iObject):
    def __init__(self, val: str):
        self.val = val

    def type(self) -> iType:
        return iType.STRING

    def value(self) -> Any:
        return self.val

    def fmt(self, *specifier) -> str:
        return self.val % (specifier)


class iNil(iObject):
    def type(self) -> iType:
        return iType.NIL

    def value(self) -> Any:
        return None

    def __repr__(self) -> str:
        return f"[{self.type()}]"


class Opcode(Enum):
    BIN_ADD = "add"
    BIN_SUB = "sub"
    BIN_MUL = "mul"
    BIN_DIV = "div"
    BIN_IN  = "in"
    BIN_MOD = "mod"
    EQ      = "eq"
    NEQ     = "neq"
    PRINT   = "print"
    PUSH    = "push"
    STORE   = "store"
    CALL    = "call"
    CALL_FN = "call_fn"
    RETURN  = "return"
    GT      = "gt"
    LT      = "lt"
    GTE     = "gte"
    LTE     = "lte"
    NOT     = "not"
    GETATTR = "getattr"
    GETITEM = "getitem"
    PUSH_GLOBAL = "push_gbloal"

    JUMP = "jump"                  # unconditional relative jump (iInteger offset)
    JUMP_IF_TRUE = "jump_if_true"  # pop cond; if true -> pc += offset
    JUMP_IF_FALSE = "jump_if_false"# pop cond; if false -> pc += offset

    MAKE_LIST = "make_list"      # arg: iInteger(n)
    MAKE_DICT = "make_dict"      # arg: iInteger(n_pairs). Pops (key, value) pairs, pushes iDict

    POP = "pop"                  # pop top of stack
    ITER_INIT = "iter_init"      # pop iterable -> push iterator
    ITER_NEXT = "iter_next"      # pop iter -> if next: push iter, item, True; else: push iter, False

    PUSH_LOCAL = "push_local"    # arg: iString(name)
    STORE_LOCAL = "store_local"  # arg: iString(name)
    
    INDEX = "index"
    SET_INDEX = "set_index"
    SET_ATTR = "set_attr"


Instruction = Tuple[Opcode, iObject]


class iFunction(iObject):
    def __init__(self, code: list[Instruction], n_params: iInteger, param_names: List[str]):
        self.code = code
        self.n_params = n_params
        self.param_names = param_names


    def type(self) -> iType:
        return iType.FUNCTION

    def value(self) -> List[Instruction]:
        return self.code

    def __repr__(self) -> str:
        return f"[{self.type()}]"


class iPyObject(iObject):
    def __init__(self, obj: Any) -> None:
        self.val = obj

    def type(self) -> iType:
        return iType.PYOBJECT

    def value(self) -> Any:
        return self.val


class iPyfunction(iObject):
    def __init__(self, func: Callable, n_params: iInteger) -> None:
        self.func = func
        self.n_params = n_params

    def type(self) -> iType:
        return iType.PYFUNCTION

    def value(self) -> Callable:
        return self.func

    def call(self, *args) -> iObject:
        return self.func(*args)


class iBoundMethod(iObject):
    def __init__(self, func: iObject, self_obj: iObject):
        self.func = func
        self.self_obj = self_obj
        self.n_params = self.func.n_params

    def type(self) -> iType:
        return iType.METHOD

    def value(self) -> Callable:
        return (self.self_obj, self.func)


class iList(iObject):
    def __init__(self, items: list[iObject]):
        self.items = items

    def type(self) -> iType:
        return iType.LIST

    def value(self):
        return self.items

    def __repr__(self) -> str:
        return f"[list] {self.items!r}"


class iDict(iObject):
    def __init__(self, items: Dict[str, iObject]):
        self.items = items

    def type(self) -> iType:
        return iType.DICT

    def value(self):
        return self.items

    def __repr__(self):
        return f"[dict] {self.items!r}"


def to_iobj(x: Any) -> iObject:
    match x:
        case None:
            return iNil()
        case iObject():
            return x
        case bool():
            return iBool(x)
        case int():
            return iInteger(x)
        case str():
            return iString(x)
        case _: # Fallback: wrap arbitrary Python objects/collections
            return iPyObject(x)


class Interpreter():
    def __init__(self) -> None:
        self.stack: List[iObject] = []
        self.globals: Dict[str, iObject] = {}
        self.local_frames: List[Dict[str, iObject]] = []
        self.trace_hook: Callable = None
        self.method_table: Dict[type, Dict[str, iObject]] = {}

        from .stdlib import load_stdlib, register_jwt_helpers,  register_list_methods
        for tup in load_stdlib():
            self.store_global(tup[0], tup[1])

        register_list_methods(self)
        register_jwt_helpers(self)

    def register_method(self, cls: type, name: str, fn: iObject) -> None:
        self.method_table.setdefault(cls, {})[name] = fn

    def resolve_method(self, obj: iObject, name: str) -> iObject | None:
        if isinstance(obj, iPyObject):
            obj = obj.value()

        for cls in type(obj).__mro__:     # walk MRO; first match wins
            table = self.method_table.get(cls)
            if table and name in table:
                return table[name]
        return None

    def _has_locals(self) -> bool:
        return len(self.local_frames) > 0

    def _locals(self) -> dict[str, iObject]:
        return self.local_frames[-1]

    def push_stack_frame(self, args, arg_names) -> None:
        frame = {name: val for name, val in zip(arg_names, args)}
        self.local_frames.append(frame)

    def pop_stack_frame(self) -> Dict:
        return self.local_frames.pop()

    def push(self, v: iObject) -> None:
        self.stack.append(v)

    def pop(self) -> iObject:
        if self.stack:
            return self.stack.pop()
        return iNil()

    def set_trace_hook(self, hook: Callable) -> None:
        self.trace_hook = hook

    def store_global(self, name: str, val: iObject) -> None:
        self.globals[name] = val

    def load_global(self, name: str) -> iObject:
        if name not in self.globals:
            return iNil()
        return self.globals[name]

    def exec(self, code: List[Instruction]) -> iObject:
        pc = 0
        stack = self.stack

        while pc < len(code):
            opcode, arg = code[pc]

            if self.trace_hook is not None:
                snapshot = list(self.stack)
                self.trace_hook(pc, opcode, arg, snapshot)

            next_pc = pc + 1

            match opcode:
                case Opcode.PUSH:
                    self.push(arg)

                case Opcode.STORE:
                    val = self.pop()
                    self.store_global(arg.value(), val)

                case Opcode.PUSH_GLOBAL:
                    val = self.load_global(arg.value())
                    self.push(val)
                    
                case Opcode.PUSH_LOCAL:
                    name = arg.value()
                    if self._has_locals() and name in self._locals():
                        self.push(self._locals()[name])
                    else:
                        self.push(iNil())

                case Opcode.STORE_LOCAL:
                    name = arg.value()
                    val = self.pop()
                    if not self._has_locals():
                        self.store_global(name, val)
                    else:
                        self._locals()[name] = val

                case Opcode.MAKE_DICT:
                    n = arg.value()
                    # expect keys then values to have been pushed in order:
                    # push key1, push val1, key2, val2 ... then MAKE_DICT(n)
                    # pop in reverse and reconstruct in original order.
                    pairs = []
                    for _ in range(n):
                        val = self.pop()
                        key = self.pop()
                        # keys should be iString (from NAME/STRING); but allow others via .value() → str
                        k = key.value() if isinstance(key, iString) else str(key.value())
                        pairs.append((k, val))
                    pairs.reverse()
                    self.push(iDict(dict(pairs)))

                case Opcode.MAKE_LIST:
                    n = arg.value()
                    items: List[iObject] = [self.pop() for _ in range(n)]
                    items.reverse()
                    self.push(iList(items))

                case Opcode.POP:
                    _ = self.pop()

                case Opcode.NOT:
                    val = self.pop()
                    self.push(iBool(not bool(val.value())))

                case Opcode.ITER_INIT:
                    iterable = self.pop()
                    it = iter(iterable.value())
                    self.push(iPyObject(it))

                case Opcode.ITER_NEXT:
                    it_obj = self.pop()
                    it = it_obj.value()
                    try:
                        item = next(it)
                        self.push(iPyObject(it))
                        self.push(to_iobj(item))
                        self.push(iBool(True))   # tells the next (jmp_if_false) instr to stay in the loop
                    except StopIteration:
                        self.push(to_iobj(it))
                        self.push(iBool(False))  # tells the next (jmp_if_false) instr to jump out of the loop

                case Opcode.BIN_ADD:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iInteger(rhs.value() + lhs.value()))

                case Opcode.BIN_SUB:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iInteger(lhs.value() - rhs.value()))

                case Opcode.BIN_MUL:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iInteger(lhs.value() * rhs.value()))

                case Opcode.BIN_DIV:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iInteger(lhs.value() / rhs.value()))

                case Opcode.BIN_MOD:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iInteger(lhs.value() % rhs.value()))

                case Opcode.EQ:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iBool(rhs.value() == lhs.value()))

                case Opcode.NEQ:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iBool(rhs.value() != lhs.value()))

                case Opcode.GT:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iBool(lhs.value() > rhs.value()))

                case Opcode.LT:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iBool(lhs.value() < rhs.value()))

                case Opcode.GTE:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iBool(lhs.value() >= rhs.value()))

                case Opcode.LTE:
                    rhs = self.pop()
                    lhs = self.pop()
                    self.push(iBool(lhs.value() <= rhs.value()))

                case Opcode.CALL_FN:
                    n = arg.value()
                    args = [self.pop() for _ in range(n)]
                    args.reverse()
                    callee = self.pop()

                    if isinstance(callee, iBoundMethod):
                        # pass self to method calls
                        args = [callee.self_obj] + args
                        n += 1
                        callee = callee.func

                    match callee:
                        case iFunction():
                            if callee.n_params.value() != n:
                                raise RuntimeError(f"arity mismatch: expected {callee.n_params.value()}, got {n}")
                            self.push_stack_frame(args, callee.param_names)
                            ret = self.exec(callee.value())
                            self.pop_stack_frame()
                            self.push(ret)

                        case iPyfunction():
                            if callee.n_params.value() != n:
                                raise RuntimeError(f"arity mismatch: expected {callee.n_params.value()}, got {n}")
                            self.push(callee.call(*args))

                        case iPyObject():
                            raise NotImplementedError()


                case Opcode.GETATTR:
                    attr_name = arg.value()
                    obj = self.pop()

                    meth = self.resolve_method(obj, attr_name)
                    if meth is not None:
                        self.push(iBoundMethod(meth, obj))
                    else:
                        try:
                            match obj:
                                case iPyObject():
                                    target = obj.value()
                                    val = getattr(target, attr_name)
                                case iObject():
                                    val = getattr(obj, attr_name)
                                case _:
                                    raise NotImplementedError()
                            self.push(to_iobj(val))
                        except Exception:
                            self.push(iNil())


                case Opcode.GETITEM:
                    container = self.pop()
                    key_obj = self.load_global(arg.value())
                    key_val = key_obj.value()
                    if isinstance(container, iList) and isinstance(key_obj, iInteger):
                        try:
                            self.push(container.value()[key_val])
                        except Exception:
                            self.push(iNil())
                    else:
                        try:
                            self.push(iPyObject(container.value().__getitem__(key_val)))
                        except Exception:
                            self.push(iNil())

                case Opcode.BIN_IN:
                    rhs = self.pop()
                    lhs = self.pop()
                    # lhs in rhs
                    try:
                        self.push(iBool(lhs.value() in rhs.value()))
                    except Exception:
                        self.push(iBool(False))

                case Opcode.PRINT:
                    val = self.pop()
                    print(val)

                case Opcode.JUMP:
                    offset = arg.value()
                    next_pc = pc + offset

                case Opcode.JUMP_IF_TRUE:
                    cond = self.pop()
                    if cond.value():
                        offset = arg.value()
                        next_pc = pc + offset
                    else:
                        next_pc = pc + 1

                case Opcode.JUMP_IF_FALSE:
                    cond = self.pop()
                    if not cond.value():
                        offset = arg.value()
                        next_pc = pc + offset
                    else:
                        next_pc = pc + 1
                        
                case Opcode.INDEX:
                    key = self.pop()
                    container = self.pop()

                    match (container, key):
                        case (iList(), iInteger()):
                            i = key.value()
                            try:
                                self.push(container.value()[i])
                            except Exception:
                                self.push(iNil())

                        case (iDict(), iString()):
                            self.push(container.value().get(key.value(), iNil()))

                        case (iDict(), iObject()):
                            kval = key.value()
                            # allow other types as key, but stringify them
                            self.push(container.value().get(str(kval, iNil())))

                        case _:
                            # fall back to Python indexing on wrapped objects/dicts/lists
                            cval = container.value()
                            kval = key.value()
                            try:
                                res = cval[kval]
                                self.push(to_iobj(res))
                            except Exception:
                                self.push(iNil())

                case Opcode.SET_INDEX:
                    val = self.pop()
                    key = self.pop()
                    container = self.pop()

                    match (container, key):
                        case (iList(), iInteger()):
                            i = key.value()
                            try:
                                container.value()[i] = val
                            except Exception:
                                # TODO: handle error
                                pass

                        # iDict by string-like key
                        case (iDict(), iObject()):
                            kval = key.value()
                            if not isinstance(kval, str):
                                kval = str(kval)
                            container.value()[kval] = val

                        case (_, _):
                            # Fallback to Python containers if you want to support iPyObject mappings/lists
                            try:
                                c = container.value()
                                k = key.value()
                                c[k] = val if isinstance(val, iObject) else val.value()
                            except Exception:
                                # TODO: handle error
                                pass

                case Opcode.SET_ATTR:
                    raise NotImplementedError()

                case Opcode.RETURN:
                    return self.pop()

                case _:
                    raise RuntimeError(f"Unhandled opcode: {opcode}")

            pc = next_pc

        return iNil()


if __name__ == "__main__":
    pass
