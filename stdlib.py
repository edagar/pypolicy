from vm import iPyObject, iPyfunction, iFunction, iObject, iInteger, iList
from lark import Lark
from codegen import CodeGen

from typing import List, Tuple



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

def _list_append(self_obj: iObject, item: iObject) -> iObject:
    assert isinstance(self_obj, iList)
    self_obj.value().append(item)
    return self_obj


def register_list_methods(interp):
    interp.register_method(iList, "append", iPyfunction(_list_append, iInteger(2)))


def range_fn(n):
    return iPyObject(range(n.value()))


def len_fn(o):
    return iInteger(len(o.value()))


def load_stdlib() -> List[Tuple[str, iPyfunction]]:
    return [
            ("range", iPyfunction(range_fn, iInteger(1))),
            ("len", iPyfunction(len_fn, iInteger(1)))
    ]
