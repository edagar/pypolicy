import pytest
from vm import Opcode, iObject, iInteger, iString


@pytest.mark.parametrize(
        "src, expected",
        [
            ("xs = [10,20,30]\nreturn xs[1]\n", 20),
            ("xs = [0,1,2]\nxs[1] := 99\nreturn xs[1]\n", 99),
            ("l = [1,2,3]\nreturn l.pop()\n", 3),
            ("l = []\n[1, 2, 3].each(i => l.append(i * 10))\nreturn l[0]\n", 10),
            ('u = {name: "alice", age: 30}\nreturn u["name"]\n', "alice"),
            ('u = {team: {lead: "bob"}}\nu["team"]["lead"] := "alice"\nreturn u["team"]["lead"]\n', "alice"),
        ]
)


def test_list_dict(eval_policy, src, expected):
    interp, bc, ast, ret = eval_policy(src)
    assert ret.value() == expected
    assert interp.stack == []


@pytest.mark.parametrize(
        "txt, opcodes",
        [
            (
                "l = [1,2]\n",
                [
                    (Opcode.PUSH, iInteger(1)),
                    (Opcode.PUSH, iInteger(2)),
                    (Opcode.MAKE_LIST, iInteger(2)),
                    (Opcode.STORE, iString("l"))
                ]
            )
        ]
)


def test_list_opcodes(eval_policy, txt, opcodes):
    interp, _, bc, _ = eval_policy(txt)
    assert bc == opcodes
    assert interp.stack == []
