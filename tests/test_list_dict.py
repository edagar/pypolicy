def test_list_literal_and_index(eval_policy):
    src = "xs = [10,20,30]\nreturn xs[1]\n"
    interp, ast, bc, ret = eval_policy(src)
    assert ret.value() == 20
    assert interp.stack == []

def test_dict_literal_and_index(eval_policy):
    src = 'u = {name: "alice", age: 30}\nreturn u["name"]\n'
    interp, ast, bc, ret  = eval_policy(src)
    assert ret.value() == "alice"
    assert interp.stack == []

def test_index_assign_list(eval_policy):
    src = "xs = [0,1,2]\nxs[1] := 99\nreturn xs[1]\n"
    interp, ast, bc, ret  = eval_policy(src)
    if interp.stack:
        breakpoint()
    assert ret.value() == 99
    assert interp.stack == []

def test_index_assign_dict_nested(eval_policy):
    src = 'u = {team: {lead: "bob"}}\nu["team"]["lead"] := "alice"\nreturn u["team"]["lead"]\n'
    interp, ast, bc, ret = eval_policy(src)
    if interp.stack:
        breakpoint()
    assert ret.value() == "alice"
    assert interp.stack == []
