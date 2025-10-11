import re


def test_if_elif_else_prints(eval_policy, capsys):
    src="""
        def greet(x)
            if x == "root":
                print("greetings, allmighty root")
            elif x == "admin":
                 print("hi there, mr admin")
            else
                print("hello, humble user")
            end
            return nil
        end

        greet("user")
        greet("root")
        greet("admin")
      """
    interp, ast, bc, ret  = eval_policy(src)
    out = capsys.readouterr().out
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    assert lines == [
        "[iType.STRING] hello, humble user",
        "[iType.STRING] greetings, allmighty root",
        "[iType.STRING] hi there, mr admin"
    ]

def test_for_over_range_no_stack_leak(eval_policy, capsys):
    src = 'for x in range(3): print(x) end\n'
    interp, ast, bc, ret  = eval_policy(src)
    # After a statement-only program, stack should be empty
    assert len(interp.stack) == 0
    out = capsys.readouterr().out
    nums = [
        int(m.group(1))
        for ln in out.splitlines()
        if (m := re.search(r"\]\s*(-?\d+)\s*$", ln))  # last int at line end
    ]
    assert nums == [0,1,2]

