import pytest

@pytest.mark.parametrize(
    "expr, expected",
    [
        ("1 == 1", True),
        ("1 != 2", True),
        ("3 > 2", True),
        ("2 < 3", True),
        ("3 >= 3", True),
        ("2 <= 1", False),
        ("2 in [1,2,3]", True),
        ("4 in [1,2,3]", False),
        ("2 in [1, 2] and 3 in [2,3]", True),
        ("2 in [1, 2] or 5 in [4,6]", True),
        ("not (1 == 2)", True),
    ]
)


def test_compare(eval_policy, expr, expected):
    interp, bc, ast, ret = eval_policy(f"return {expr}\n")
    assert ret.value() == expected
    assert interp.stack == []

