from lark import Lark
from .vm import iPyObject, iPyfunction, iFunction, iObject, iInteger, iList, iString, Interpreter, iDict
from .codegen import CodeGen
from .dsl_method import register_dsl_method

from typing import List, Tuple, Any


def iList_map_function():
    return """
    def __list_map(l, f)
        ret = []
        for x in l
            z = f(x)
            ret.append(z)
        end
        return ret
    end
    """

def iList_each_function():
    return """
    def __list_each(l, f)
        for x in l
            f(x)
        end
    end
    """


def iList_filter_function():
    return """
    def __list_filter(l, f)
        ret = []
        for x in l
            cond = f(x)
            if cond:
                ret.append(x)
            end
        end
        return ret
    end
    """

def _list_append(self_obj: iObject, item: iObject) -> iObject:
    assert isinstance(self_obj, iList)
    self_obj.value().append(item)
    return self_obj


def register_list_methods(interp: Interpreter):
    interp.register_method(iList, "append", iPyfunction(_list_append, iInteger(2)))
    interp.register_method(iList, "pop", iPyfunction(lambda l: l.value().pop(), iInteger(1)))
    register_dsl_method(
        interp,
        src=iList_each_function(),
        func_name="__list_each",
        attach_as="each",
        attach_to=iList
    )
    register_dsl_method(
        interp,
        src=iList_map_function(),
        func_name="__list_map",
        attach_as="map",
        attach_to=iList
    )
    register_dsl_method(
            interp,
            src=iList_filter_function(),
            func_name="__list_filter",
            attach_as="filter",
            attach_to=iList
    )
    register_dsl_method(
        interp,
        src=iList_each_function(),
        func_name="__list_each",
        attach_as="each",
        attach_to=range
    )
    register_dsl_method(
            interp,
            src=iList_filter_function(),
            func_name="__list_filter",
            attach_as="filter",
            attach_to=range
    )


def __str_fmt(s, *args) -> iString:
    return iString(s.value() % tuple([x.value() for x in args]))


def __str_join(s: iString, l: iList) -> iString:
    return iString(s.value().join([x.value() for x in l.value()]))


def register_str_methods(interp: Interpreter):
    interp.register_method(iString, "fmt", iPyfunction(__str_fmt , iInteger(0), varargs=True))
    interp.register_method(iString, "join", iPyfunction(__str_join , iInteger(2)))


def register_dict_methods(interp: Interpreter):
    interp.register_method(iDict, "keys", iPyfunction(lambda d: iList([x for x in d.value().keys()]), iInteger(1)))


def range_fn(n):
    return iPyObject(range(n.value()))


def len_fn(o):
    return iInteger(len(o.value()))


def load_stdlib(interp: Interpreter):
    register_list_methods(interp)
    register_str_methods(interp)
    register_dict_methods(interp)

    _globals = [
            ("range", iPyfunction(range_fn, iInteger(1))),
            ("len", iPyfunction(len_fn, iInteger(1)))
    ]
    for t in _globals:
        interp.store_global(t[0], t[1])
