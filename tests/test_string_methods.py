import pytest
from pypolicy.vm import iString

@pytest.mark.parametrize(
    "expr, expected",
    [
        ('"%s, %s".fmt("hello", "world")', iString("hello, world")),
        ('"%s %s %d".fmt("one", "two", 3)', iString("one two 3")),
        ('",".join(["one", "two", "three"])', iString("one,two,three")),
    ]
)


def test_string_methods(eval_policy, expr, expected):
    interp, bc, ast, ret = eval_policy(f"return {expr}\n")
    assert ret.value() == expected
    assert interp.stack == []
