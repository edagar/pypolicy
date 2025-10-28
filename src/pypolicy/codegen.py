from __future__ import annotations
from typing import List, Tuple, Optional, Union, Callable

from lark import Tree, Token
from .vm import (
    Opcode, Instruction,
    iInteger, iString, iBool, iNil, iPyObject, iObject, iFunction
)

class CodeGenError(Exception): pass

class CodeGen:
    def __init__(self):
        self.code: List[Instruction] = []
        # stack of local-variable name sets (one per function scope)
        self.local_scopes: List[set[str]] = []

    # ------------- low-level -------------
    def emit(self, op: Opcode, arg: iObject) -> int:
        idx = len(self.code)
        self.code.append((op, arg))
        return idx

    def emit_jump(self, op: Opcode) -> int:
        return self.emit(op, iInteger(0))

    def patch(self, jidx: int, target_idx: int) -> None:
        offset = target_idx - jidx
        op, _ = self.code[jidx]
        self.code[jidx] = (op, iInteger(offset))

    # ------------- entry -------------
    def compile(self, tree: Tree) -> List[Instruction]:
        self.code = []
        self._gen(tree)
        return self.code

    # ------------- dispatch -------------
    def _gen(self, node: Union[Tree, Token]):
        if node is None:
            return

        if isinstance(node, Token):
            return

        if not isinstance(node, Tree):
            raise CodeGenError(f"Unknown node {node!r}")

        fn = getattr(self, f"gen_{node.data}", None)

        if not fn:
            raise CodeGenError(f"No generator for {node.data}")

        return fn(node.children)

    # ------------- program / stmts -------------
    def gen_start(self, children): 
        for c in children:
            self._gen(c)
            if self.code and self.code[-1][0] == Opcode.RETURN:
                break


    def gen_assign(self, children):
        name_tok, expr = children[0], children[1]
        name = str(name_tok)
        self._gen(expr)
        if self.local_scopes and name in self.local_scopes[-1]:
            self.emit(Opcode.STORE_LOCAL, iString(name))
        elif self.local_scopes:
            # inside a function: new locals by default
            self.local_scopes[-1].add(name)
            self.emit(Opcode.STORE_LOCAL, iString(name))
        else:
            self.emit(Opcode.STORE, iString(name))

    def gen_print_stmt(self, children):
        # Expect exactly one expression tree after the RETURN token.
        expr = next((ch for ch in children if hasattr(ch, "data")), None)

        if expr is not None:
            self._gen(expr)
        else:
            self.emit(Opcode.PUSH, iNil())

        self.emit(Opcode.PRINT, iNil())

    # ------------- functions -------------
    def gen_func_def(self, children):
        """
        func_def: DEF NAME "(" [param_list] ")" block END -> func_def
        Children may include terminals (DEF, LPAR, RPAR, END). We extract:
        - first NAME token as the function name
        - optional Tree('param_list')
        - Tree('block')
        """
        name_tok: Token | None = None
        plist: Tree | None = None
        body: Tree | None = None

        # 1) find NAME
        i = 0
        while i < len(children):
            ch = children[i]
            if isinstance(ch, Token) and ch.type == "NAME":
                name_tok = ch
                i += 1
                break
            i += 1
        if name_tok is None:
            raise CodeGenError("func_def: missing function name")

        # 2) find optional param_list (next Tree with data == 'param_list')
        j = i
        while j < len(children):
            ch = children[j]
            if isinstance(ch, Tree) and ch.data == "param_list":
                plist = ch
                j += 1
                break
            elif isinstance(ch, Tree) and ch.data == "block":
                # no params; block encountered
                break
            j += 1

        # 3) find block (first Tree with data == 'block' after plist search)
        k = j
        while k < len(children):
            ch = children[k]
            if isinstance(ch, Tree) and ch.data == "block":
                body = ch
                break
            k += 1
        if body is None:
            raise CodeGenError("func_def: missing block")

        # 4) params list
        params: list[str] = []
        if plist is not None:
            for t in plist.children:
                if isinstance(t, Token) and t.type == "NAME":
                    params.append(str(t))

        # 5) compile body in a fresh scope
        inner = CodeGen()
        inner.local_scopes.append(set(params))
        inner._gen(body)
        # ensure function returns something (implicit nil) if no explicit return
        inner.emit(Opcode.PUSH, iNil())
        inner.emit(Opcode.RETURN, iNil())

        # 6) make function object and store to globals under the real name
        fn_obj = iFunction(inner.code, iInteger(len(params)), params)
        self.emit(Opcode.PUSH, fn_obj)
        self.emit(Opcode.STORE, iString(str(name_tok)))


    def gen_return_stmt(self, children):
        # Expect exactly one expression tree after the RETURN token.
        expr = next((ch for ch in children if hasattr(ch, "data")), None)

        if expr is not None:
            self._gen(expr)
        else:
            self.emit(Opcode.PUSH, iNil())

        self.emit(Opcode.RETURN, iNil())


    def gen_block(self, children):
        for c in children:
            self._gen(c)
            # If the last emitted instruction is RETURN, stop generating this block
            if self.code and self.code[-1][0] == Opcode.RETURN:
                break


    def gen_lambda(self, children):
        # children: [lambda_params, lambda_body] (plus tokens)
        params_tree = None
        body_tree = None
        for ch in children:
            if isinstance(ch, Tree):
                if ch.data in ("lambda_param_single", "lambda_param_list"):
                    params_tree = ch
                elif ch.data.startswith("lambda_body_"):
                    body_tree = ch

        # Collect param names
        params = []
        if params_tree:
            if params_tree.data == "lambda_param_single":
                t = params_tree.children[0]
                if isinstance(t, Token) and t.type == "NAME":
                    params.append(str(t))
            elif params_tree.data == "lambda_param_list":
                # children may be NAME tokens or a name_list Tree
                for t in params_tree.children:
                    if isinstance(t, Token) and t.type == "NAME":
                        params.append(str(t))
                    elif isinstance(t, Tree) and t.data == "name_list":
                        for c in t.children:
                            if isinstance(c, Token) and c.type == "NAME":
                                params.append(str(c))

        # Compile body into a nested function
        inner = CodeGen()
        inner.local_scopes.append(set(params))

        if body_tree and body_tree.data == "lambda_body_expr":
            # single-expression body: value → RETURN
            # find the expr Tree child
            expr = next((c for c in body_tree.children if isinstance(c, Tree)), None)
            inner._gen(expr)
            inner.emit(Opcode.RETURN, iNil())
        else:
            # block body: compile block; allow explicit returns inside
            # if it falls through, return nil implicitly
            block = next((c for c in body_tree.children if isinstance(c, Tree) and c.data == "block"), None)
            inner._gen(block)
            inner.emit(Opcode.PUSH, iNil())
            inner.emit(Opcode.RETURN, iNil())

        fn_obj = iFunction(inner.code, iInteger(len(params)), params)
        self.emit(Opcode.PUSH, fn_obj)



    # ------------- for-loops -------------
    def gen_for_stmt(self, children):
        # Grammar: FOR NAME IN expr block END
        var_name = None
        iterable_expr = None
        body = None
        seen_in = False

        for ch in children:
            if isinstance(ch, Token):
                if ch.type == "NAME" and var_name is None:
                    var_name = str(ch)
                elif ch.type == "IN":
                    seen_in = True
            elif isinstance(ch, Tree):
                if ch.data == "block":
                    body = ch
                    break
                # the first Tree we see *after* IN is the iterable expression
                if seen_in and iterable_expr is None:
                    iterable_expr = ch

        if var_name is None or iterable_expr is None or body is None:
            raise CodeGenError("for_stmt: missing pieces (var, iterable, or block)")

        # Evaluate iterable (full postfix like range(10)), then init iterator
        self._gen(iterable_expr)
        self.emit(Opcode.ITER_INIT, iNil())

        loop_top = len(self.code)
        self.emit(Opcode.ITER_NEXT, iNil())
        j_exit = self.emit_jump(Opcode.JUMP_IF_FALSE)

        # Bind loop variable in the nearest local scope if present
        if self.local_scopes:
            self.local_scopes[-1].add(var_name)
            self.emit(Opcode.STORE_LOCAL, iString(var_name))
        else:
            self.emit(Opcode.STORE, iString(var_name))

        self._gen(body)

        j_back = self.emit_jump(Opcode.JUMP)
        self.patch(j_back, loop_top)

        exit_idx = len(self.code)
        self.patch(j_exit, exit_idx)
        self.emit(Opcode.POP, iNil())  # pop iterator


    # ------------- literals / names / lists -------------
    def gen_number(self, children): 
        self.emit(Opcode.PUSH, iInteger(int(str(children[0]))))

    def gen_string(self, children):
        s = str(children[0]); s = s[1:-1] if len(s)>=2 and s[0] in "\"'" else s
        self.emit(Opcode.PUSH, iString(s))

    def gen_true(self, _): self.emit(Opcode.PUSH, iBool(True))
    def gen_false(self, _): self.emit(Opcode.PUSH, iBool(False))

    def gen_var(self, children):
        name = str(children[0])
        if self.local_scopes and (name in self.local_scopes[-1]):
            self.emit(Opcode.PUSH_LOCAL, iString(name))
        else:
            self.emit(Opcode.PUSH_GLOBAL, iString(name))

    def gen_list(self, children):
        # "[" [arg_list] "]"  -> build via MAKE_LIST
        count = 0
        if children:
            arg_list = children[0]
            if arg_list is None:
                # []  (no elements)
                count = 0
            elif isinstance(arg_list, Tree) and arg_list.data == "arg_list":
                for expr in arg_list.children:
                    self._gen(expr)
                count = len(arg_list.children)
            else:
                # Extremely rare fallback: single expression treated as one element
                self._gen(arg_list)
                count = 1
        self.emit(Opcode.MAKE_LIST, iInteger(count))


    def gen_dict(self, children):
        """
        dict_literal: "{" [dict_items] "}" -> dict
        dict_items: dict_item ("," dict_item)*
        dict_item: dict_key ":" expr
        dict_key: NAME -> key_name | STRING -> key_string
        """
        n_pairs = 0
        if children and children != [None]: # empty dict literal produces children -> [None]
            items = children[0]  # Tree('dict_items') or a single dict_item
            dict_elems = items.children if isinstance(items, Tree) and items.data == "dict_items" else [items]
            for it in dict_elems:
                # it: Tree('dict_item', [dict_key, expr])
                key_node, val_node = it.children[0], it.children[1]
                # push key
                if isinstance(key_node, Tree) and key_node.data == "key_name":
                    name_tok = key_node.children[0]
                    self.emit(Opcode.PUSH, iString(str(name_tok)))
                elif isinstance(key_node, Tree) and key_node.data == "key_string":
                    s = str(key_node.children[0]); s = s[1:-1] if len(s)>=2 and s[0] in "\"'" else s
                    self.emit(Opcode.PUSH, iString(s))
                else:
                    # shouldn’t happen with this grammar, fallback:
                    self._gen(key_node)
                # push value
                self._gen(val_node)
                n_pairs += 1
        self.emit(Opcode.MAKE_DICT, iInteger(n_pairs))


    def gen_func_call(self, children):
        name = str(children[0])
        if len(children) > 1 and isinstance(children[1], Tree) and children[1].data == "arg_list":
            for arg in children[1].children: self._gen(arg)
        self.emit(Opcode.CALL_FN, iString(name))


    def _pick_binary_exprs(self, children):
        # Returns (left_expr_tree, right_expr_tree), skipping terminals (Tokens)
        exprs = [ch for ch in children if isinstance(ch, Tree)]
        if len(exprs) != 2:
            raise CodeGenError(f"expected 2 expr children, got {len(exprs)}: {children!r}")
        return exprs[0], exprs[1]


    def _bin(self, children, op: Opcode):
        left, right = self._pick_binary_exprs(children)
        self._gen(left)
        self._gen(right)
        self.emit(op, iNil())

    def gen_add(self, c): self._bin(c, Opcode.BIN_ADD)
    def gen_sub(self, c): self._bin(c, Opcode.BIN_SUB)
    def gen_mul(self, c): self._bin(c, Opcode.BIN_MUL)
    def gen_div(self, c): self._bin(c, Opcode.BIN_DIV)
    def gen_mod(self, c): self._bin(c, Opcode.BIN_MOD)
    def gen_neg(self, c):
        self.emit(Opcode.PUSH, iInteger(0)); self._gen(c[0]); self.emit(Opcode.BIN_SUB, iNil())

    def gen_eq(self, c): self._bin(c, Opcode.EQ)
    def gen_ne(self, c): self._bin(c, Opcode.NEQ)
    def gen_gt(self, c): self._bin(c, Opcode.GT)
    def gen_lt(self, c): self._bin(c, Opcode.LT)
    def gen_ge(self, c): self._bin(c, Opcode.GTE)
    def gen_le(self, c): self._bin(c, Opcode.LTE)
    def gen_in_op(self, c): self._bin(c, Opcode.BIN_IN)

    # short-circuit logic uses your jump opcodes (from previous version)
    def gen_not_op(self, children):
        expr = next((ch for ch in children if hasattr(ch, "data")), None)
        if expr is None:
             # default to false -> not false => true (rare)
            self.emit(Opcode.PUSH, iBool(False))
        else:
            self._gen(expr)
        self.emit(Opcode.NOT, iNil())

    def gen_and_op(self, children):
        # a and b  -> if a is false, result False; else result b
        left, right = self._pick_binary_exprs(children)

        # eval left
        self._gen(left)
        # if left is false -> jump to push_false
        j_false = self.emit_jump(Opcode.JUMP_IF_FALSE)

        # left was true -> evaluate right; its value is the result
        self._gen(right)
        j_end = self.emit_jump(Opcode.JUMP)

        # false path: push False as the result
        false_pos = len(self.code)
        self.patch(j_false, false_pos)
        self.emit(Opcode.PUSH, iBool(False))

        # end
        end_pos = len(self.code)
        self.patch(j_end, end_pos)

    def gen_or_op(self, children):
        # a or b  -> if a is true, result True; else result b
        left, right = self._pick_binary_exprs(children)

        # eval left
        self._gen(left)
        # if left is true -> jump to push_true
        j_true = self.emit_jump(Opcode.JUMP_IF_TRUE)

        # left was false -> evaluate right; its value is the result
        self._gen(right)
        j_end = self.emit_jump(Opcode.JUMP)

        # true path: push True as the result
        true_pos = len(self.code)
        self.patch(j_true, true_pos)
        self.emit(Opcode.PUSH, iBool(True))

        # end
        end_pos = len(self.code)
        self.patch(j_end, end_pos)


    def gen_if_stmt(self, children):
        """
        if_stmt: IF expr [":"] block (ELIF expr [":"] block)* [ELSE [":"] block] END
        Build clauses = [(cond_tree, block_tree), ...], else_block = Tree('block')|None
        """
        clauses = []
        else_block = None

        i = 0
        n = len(children)
        mode = None  # 'if', 'elif', 'else'
        pending_cond = None

        while i < n:
            ch = children[i]
            if isinstance(ch, Token):
                t = ch.type
                if t == "IF":
                    mode = "if"; pending_cond = None
                elif t == "ELIF":
                    mode = "elif"; pending_cond = None
                elif t == "ELSE":
                    mode = "else"; pending_cond = None
                # ignore ":" and "END" tokens here
            elif isinstance(ch, Tree):
                if ch.data == "block":
                    if mode in ("if", "elif"):
                        if pending_cond is None:
                            raise CodeGenError("if_stmt: missing condition before block")
                        clauses.append((pending_cond, ch))
                        pending_cond = None
                    elif mode == "else":
                        else_block = ch
                    else:
                        raise CodeGenError("if_stmt: unexpected block")
                else:
                    # this Tree is the condition expr for IF/ELIF
                    if mode in ("if", "elif"):
                        pending_cond = ch
                    # ignore expr in 'else' (shouldn't happen)
            i += 1

        # --- emit code ---
        end_jumps = []
        for cond, block in clauses:
            # condition
            self._gen(cond)
            # if false -> jump to next clause/else
            jfalse = self.emit_jump(Opcode.JUMP_IF_FALSE)
            # then-block
            self._gen(block)
            # jump to end after then
            jend = self.emit_jump(Opcode.JUMP)
            end_jumps.append(jend)
            # patch false to here (start of next clause / else)
            self.patch(jfalse, len(self.code))

        # else (if any)
        if else_block is not None:
            self._gen(else_block)

        # patch all end jumps to end
        end_label = len(self.code)
        for j in end_jumps:
            self.patch(j, end_label)

    def gen_expr_stmt(self, children):
        # Evaluate the expression (may push a value)
        self._gen(children[0])
        # Discard the result so the loop’s stack invariant holds
        self.emit(Opcode.POP, iNil())

    def gen_lvalue_assign(self, children):
        # lvalue_assign: NAME lvalue_chain ":=" expr
        name_tok, chain_node, value_expr = children[0], children[1], children[2]
        base = str(name_tok)

        # Load base container (prefer local)
        if self.local_scopes and (base in self.local_scopes[-1]):
            self.emit(Opcode.PUSH_LOCAL, iString(base))
        else:
            self.emit(Opcode.PUSH_GLOBAL, iString(base))

        # Traverse all but last hop
        hops = chain_node.children  # Trees: l_attr or l_index
        for hop in hops[:-1]:
            if hop.data == "l_attr":
                name_tok = hop.children[0]
                self.emit(Opcode.GETATTR, iString(str(name_tok)))
            elif hop.data == "l_index":
                key_expr = hop.children[0]
                self._gen(key_expr)
                self.emit(Opcode.INDEX, iNil())
            else:
                raise CodeGenError(f"unknown lvalue hop: {hop.data}")

            # Final hop decides setter
        last = hops[-1]
        if last.data == "l_attr":
            name_tok = last.children[0]
            self._gen(value_expr)
            self.emit(Opcode.SET_ATTR, iString(str(name_tok)))
        elif last.data == "l_index":
            key_expr = last.children[0]
            self._gen(key_expr)
            self._gen(value_expr)
            self.emit(Opcode.SET_INDEX, iNil())
        else:
            raise CodeGenError(f"unknown final hop: {last.data}")

        # Optional cleanup if your stmt layer doesn't POP
        # self.emit(Opcode.POP, iNil())

    def gen_postfix_call(self, children):
        return self.gen_postfix(children)


    def gen_postfix(self, children):
        """
        postfix: atom suffix*
        suffix : "(" [arg_list] ")" -> call
               | "[" expr "]"       -> index
               | "." NAME           -> attr
        """
        # 1) compile the base (callee/receiver)
        self._gen(children[0])

        # 2) fold each suffix left-to-right
        for suf in children[1:]:
            if suf is None:
                continue  # defensive: nothing to do

            dt = getattr(suf, "data", None)

            if dt == "index":
                # "[" expr "]"
                key_expr = suf.children[0] if suf.children else None
                self._gen(key_expr)                 # push key (safe if None: no-op)
                self.emit(Opcode.INDEX, iNil())     # pop key, pop container → push element

            elif dt == "attr":
                # "." NAME
                name_tok = suf.children[0]          # Token(NAME)
                self.emit(Opcode.GETATTR, iString(str(name_tok)))

            elif dt == "call":
                # "(" [arg_list] ")"
                argc = 0
                if suf.children:
                    child = suf.children[0]
                    if child is None:
                        # f() — no args
                        pass
                    elif isinstance(child, Tree) and child.data == "arg_list":
                        for expr in child.children:
                            self._gen(expr)
                            argc += 1
                    else:
                        # ultra-rare fallback: treat as single expr
                        self._gen(child)
                        argc = 1

                # callee is already on stack, args (if any) are pushed now
                self.emit(Opcode.CALL_FN, iInteger(argc))

            else:
                raise CodeGenError(f"Unknown suffix node: {suf!r}")




    def gen_call(self, _):  # handled inside gen_postfix
        return
    def gen_index(self, _): return
    def gen_attr(self, _): return


    # passthroughs
    def gen_arg_list(self, _): return
