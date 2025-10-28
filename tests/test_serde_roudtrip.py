import pytest

from pypolicy.parse import compile_source
from pypolicy.vm import Interpreter, Opcode, iInteger
from pypolicy.serde import serialize, deserialize

def _exec(code):
    vm = Interpreter()
    return vm.exec(code)


def test_simple_roundtrip():
    src = """
    return 1 + 2 * 3
    """
    code = compile_source(src)
    blob = serialize(code)
    code2 = deserialize(blob)
    assert _exec(code2) == 7


def test_functions_and_lists_roundtrip():
    src = """
    def add(x, y)
        return x + y
    end
    xs = []
    for i in range(3):
        xs.append(add(i, 10))
    end
    return xs[1]
    """
    code = compile_source(src)
    blob = serialize(code)
    code2 = deserialize(blob)
    assert _exec(code2) == iInteger(11)


@pytest.mark.xfail(reason="Closures are not supported yet", strict=True)
def test_nested_lambda_roundtrip():
    src = """
    def mk(n)
        f = (x) => x + n
        return f(41)
    end
    return mk(1)
    """
    code = compile_source(src)
    blob = serialize(code)
    code2 = deserialize(blob)
    assert _exec(code2) == iInteger(42)

def test_nested_lambda_roundtrip_no_capture():
    # No capture: lambda takes both x and n explicitly
    src = """
        def mk()
            return (x, n) => x + n
        end
        f = mk()
        return f(41, 1)
    """

    code = compile_source(src)
    blob = serialize(code)
    code2 = deserialize(blob)
    assert _exec(code2) == iInteger(42)

