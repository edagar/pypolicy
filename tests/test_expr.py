def test_number_math(eval_policy):
    src = "return (1 + 2) * 3\n"
    interp, ast, bc, ret = eval_policy(src)
    assert ret.value() == 9
    assert interp.stack == []


def test_comparison_and_in(eval_policy):
    src = "return 2 in [1,2,3] and (3 <= 3) and (4 > 1)\n"
    interp, ast, bc, ret = eval_policy(src)
    assert ret.value() == True
    assert interp.stack == []


def test_boolean_not(eval_policy):
    src = "return not (1 == 2)\n"
    interp, ast, bc, ret = eval_policy(src)
    assert ret.value() is True
    assert interp.stack == []
