"""Convert Python AST expressions into Desmos LaTeX."""

from __future__ import annotations

import ast
import math
from typing import Optional, Sequence, Union

from pydesmos.errors import UnsupportedPythonError
from pydesmos.names import (
    HELPER_NAMES,
    LATEX_FUNCS,
    OPERATORNAME_FUNCS,
    SPECIAL_IDENTS,
    func_to_latex,
    ident_to_latex,
)

Number = Union[int, float]


def to_latex(node: ast.AST, *, source: Optional[str] = None) -> str:
    """Render a Python expression AST node as Desmos LaTeX."""
    return LatexVisitor(source=source).emit(node)


def unwrap_expr(node: ast.AST) -> ast.AST:
    """Return the expression inside an ``Expr`` statement, else ``node``."""
    if isinstance(node, ast.Expr):
        return node.value
    return node


class LatexVisitor:
    """Walk a Python expression and emit Desmos LaTeX."""

    def __init__(self, source: Optional[str] = None) -> None:
        self.source = source

    def emit(self, node: ast.AST) -> str:
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is None:
            raise UnsupportedPythonError(
                f"{type(node).__name__} expressions cannot be mapped to Desmos",
                node,
            )
        return method(node)

    def visit_Expression(self, node: ast.Expression) -> str:
        return self.emit(node.body)

    def visit_Module(self, node: ast.Module) -> str:
        raise UnsupportedPythonError("a full module is not a single expression", node)

    # -- literals -----------------------------------------------------------

    def visit_Constant(self, node: ast.Constant) -> str:
        value = node.value
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if math.isnan(value):
                raise UnsupportedPythonError("NaN is not a Desmos value", node)
            if math.isinf(value):
                return r"-\infty" if value < 0 else r"\infty"
            # Keep compact, stable representation.
            text = format(value, ".15g")
            if text.startswith("-"):
                return f"-{text[1:]}" if "." in text or "e" in text else text
            return text
        if isinstance(value, str):
            # String literals are used for raw latex / labels; escape for text.
            return value
        if value is None:
            raise UnsupportedPythonError("None has no Desmos equivalent", node)
        raise UnsupportedPythonError(
            f"literal {type(value).__name__} is not supported", node
        )

    def visit_Name(self, node: ast.Name) -> str:
        return ident_to_latex(node.id)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        operand = self.emit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            if _is_atom(node.operand):
                return f"-{operand}"
            return rf"-\left({operand}\right)"
        if isinstance(node.op, ast.Not):
            return self._not(node.operand)
        if isinstance(node.op, ast.Invert):
            raise UnsupportedPythonError("bitwise invert (~) is not supported", node)
        raise UnsupportedPythonError(f"unary operator {type(node.op).__name__}", node)

    def visit_BinOp(self, node: ast.BinOp) -> str:
        op = node.op
        left = self.emit(node.left)
        right = self.emit(node.right)
        if isinstance(op, ast.Add):
            return f"{left}+{right}"
        if isinstance(op, ast.Sub):
            if _needs_paren_on_right_of_sub(node.right):
                right = rf"\left({right}\right)"
            return f"{left}-{right}"
        if isinstance(op, ast.Mult):
            return self._multiply(node.left, node.right, left, right)
        if isinstance(op, ast.Div):
            return rf"\frac{{{left}}}{{{right}}}"
        if isinstance(op, ast.FloorDiv):
            return rf"\operatorname{{floor}}\left(\frac{{{left}}}{{{right}}}\right)"
        if isinstance(op, ast.Mod):
            return rf"\operatorname{{mod}}\left({left},{right}\right)"
        if isinstance(op, ast.Pow):
            base = left if _is_atom(node.left) else rf"\left({left}\right)"
            return f"{base}^{{{right}}}"
        if isinstance(op, ast.MatMult):
            # Desmos matrix multiplication is juxtaposition / \cdot.
            return rf"{left}\cdot{{{right}}}"
        raise UnsupportedPythonError(f"operator {type(op).__name__} is not supported", node)

    def visit_BoolOp(self, node: ast.BoolOp) -> str:
        parts = [self.emit(v) for v in node.values]
        if isinstance(node.op, ast.And):
            # In Desmos restrictions, a comma means AND.
            return ",".join(parts)
        if isinstance(node.op, ast.Or):
            # Desmos has no dedicated OR in restrictions; piecewise-style
            # disjunction is emitted as a piecewise that is 1 when any branch is.
            # For conditions used inside piecewise, callers should prefer
            # multiple branches. Here we emit a numeric OR: {c1:1, c2:1, ..., 0}
            inner = ",".join(f"{p}:1" for p in parts) + ",0"
            return rf"\left\{{{inner}\right\}}"
        raise UnsupportedPythonError("unknown boolean operator", node)

    def visit_Compare(self, node: ast.Compare) -> str:
        left_node = node.left
        left = self.emit(left_node)
        chunks: list[str] = []
        for op, comparator in zip(node.ops, node.comparators):
            right = self.emit(comparator)
            chunks.append(f"{left}{_cmp_op(op, comparator)}{right}")
            left_node = comparator
            left = right
        if len(chunks) == 1:
            return chunks[0]
        return ",".join(chunks)

    def visit_IfExp(self, node: ast.IfExp) -> str:
        test = self.emit(node.test)
        body = self.emit(node.body)
        orelse = self.emit(node.orelse)
        return rf"\left\{{{test}:{body},{orelse}\right\}}"

    def visit_Call(self, node: ast.Call) -> str:
        if node.keywords and _call_name(node) not in (
            "slider",
            "point",
            "point3d",
            "segment",
            "polygon",
            "circle",
            "parametric",
            "polar",
            "tone",
            "ticker",
            "action",
            "assign",
            "rgb",
            "hsv",
            "raw",
            "latex",
            "surface",
            "sphere",
            "triangle",
            "inequality",
        ):
            # Keyword args on user math functions are not Desmos syntax.
            if not _is_helper_call(node):
                raise UnsupportedPythonError(
                    "keyword arguments on math calls are not supported", node
                )
        name = _call_name(node)
        if name is None:
            if isinstance(node.func, ast.Attribute):
                return self._attribute_call(node)
            raise UnsupportedPythonError("computed function calls are not supported", node)
        if name in HELPER_NAMES:
            return self._helper_as_expr(node, name)
        return self._math_call(node, name)

    def visit_Attribute(self, node: ast.Attribute) -> str:
        # math.pi, math.e, math.tau
        if isinstance(node.value, ast.Name) and node.value.id in {"math", "np"}:
            return self.visit_Name(ast.Name(id=node.attr, ctx=ast.Load()))
        raise UnsupportedPythonError(
            f"attribute access ({_unparse(node)}) is not supported", node
        )

    def visit_Subscript(self, node: ast.Subscript) -> str:
        value = self.emit(node.value)
        sl = node.slice
        if isinstance(sl, ast.Slice):
            return self._slice(value, sl)
        index = self.emit(sl)
        return rf"{value}\left[{index}\right]"

    def visit_Slice(self, node: ast.Slice) -> str:
        raise UnsupportedPythonError("a slice must be used as a subscript", node)

    def visit_List(self, node: ast.List) -> str:
        if node.elts and all(isinstance(e, ast.Starred) for e in node.elts):
            raise UnsupportedPythonError("starred list items are not supported", node)
        inner = ",".join(self.emit(e) for e in node.elts)
        return rf"\left[{inner}\right]"

    def visit_Tuple(self, node: ast.Tuple) -> str:
        inner = ",".join(self.emit(e) for e in node.elts)
        return rf"\left({inner}\right)"

    def visit_ListComp(self, node: ast.ListComp) -> str:
        return self._comprehension(node.elt, node.generators, node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> str:
        # Bare generator; callers like sum() handle this specially.
        return self._comprehension(node.elt, node.generators, node)

    def visit_SetComp(self, node: ast.SetComp) -> str:
        raise UnsupportedPythonError("set comprehensions are not supported", node)

    def visit_DictComp(self, node: ast.DictComp) -> str:
        raise UnsupportedPythonError("dict comprehensions are not supported", node)

    def visit_Dict(self, node: ast.Dict) -> str:
        raise UnsupportedPythonError("dict literals are not supported", node)

    def visit_Set(self, node: ast.Set) -> str:
        raise UnsupportedPythonError("set literals are not supported", node)

    def visit_Lambda(self, node: ast.Lambda) -> str:
        raise UnsupportedPythonError(
            "bare lambdas are only supported as the right-hand side of an assignment "
            "(e.g. f = lambda x: x**2)",
            node,
        )

    def visit_Starred(self, node: ast.Starred) -> str:
        raise UnsupportedPythonError("*unpacking is not supported", node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> str:
        raise UnsupportedPythonError("walrus operator := is not supported", node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> str:
        raise UnsupportedPythonError("f-strings are not supported", node)

    def visit_FormattedValue(self, node: ast.FormattedValue) -> str:
        raise UnsupportedPythonError("f-string formatting is not supported", node)

    # -- helpers used as expressions ----------------------------------------

    def _helper_as_expr(self, node: ast.Call, name: str) -> str:
        """Emit a helper used inside a larger expression (not a statement)."""
        args = node.args
        if name in {"point", "point3d"}:
            coords = [self.emit(a) for a in args]
            if not coords:
                raise UnsupportedPythonError("point() needs coordinates", node)
            return rf"\left({','.join(coords)}\right)"
        if name == "slider":
            if not args:
                raise UnsupportedPythonError("slider() needs a value", node)
            return self.emit(args[0])
        if name in {"raw", "latex"}:
            if not args:
                raise UnsupportedPythonError(f"{name}() needs a string", node)
            if not isinstance(args[0], ast.Constant) or not isinstance(args[0].value, str):
                raise UnsupportedPythonError(f"{name}() requires a string literal", node)
            return args[0].value
        if name == "rgb":
            inner = ",".join(self.emit(a) for a in args)
            return rf"\operatorname{{rgb}}\left({inner}\right)"
        if name == "hsv":
            inner = ",".join(self.emit(a) for a in args)
            return rf"\operatorname{{hsv}}\left({inner}\right)"
        if name == "tone":
            inner = ",".join(self.emit(a) for a in args)
            return rf"\operatorname{{tone}}\left({inner}\right)"
        if name == "polygon":
            inner = ",".join(self.emit(a) for a in args)
            return rf"\operatorname{{polygon}}\left({inner}\right)"
        if name == "triangle":
            inner = ",".join(self.emit(a) for a in args)
            return rf"\operatorname{{triangle}}\left({inner}\right)"
        if name == "circle":
            return circle_latex(args, fill=False, visitor=self)
        if name == "segment":
            if len(args) != 2:
                raise UnsupportedPythonError("segment(a, b) needs two endpoints", node)
            return (
                r"\operatorname{polygon}\left("
                + self.emit(args[0])
                + ","
                + self.emit(args[1])
                + r"\right)"
            )
        if name == "sphere":
            return sphere_latex(args, visitor=self)
        if name == "surface":
            if not args:
                raise UnsupportedPythonError("surface() needs an expression", node)
            return rf"z={self.emit(args[0])}"
        if name == "polar":
            if not args:
                raise UnsupportedPythonError("polar() needs r(θ)", node)
            r_expr = self.emit(args[0])
            r_expr = _replace_ident(r_expr, "t", r"\theta")
            return rf"r={r_expr}"
        if name == "parametric":
            coords = [self.emit(a) for a in args]
            if len(coords) not in {2, 3}:
                raise UnsupportedPythonError(
                    "parametric() needs 2 (x, y) or 3 (x, y, z) components", node
                )
            return rf"\left({','.join(coords)}\right)"
        if name == "action":
            return action_latex_from_call(node, self)
        if name == "assign":
            return assign_latex_from_call(node, self)
        if name == "inequality":
            if not args:
                raise UnsupportedPythonError("inequality() needs an expression", node)
            return self.emit(args[0])
        # ticker / note / folder / viewport / slider as a nested expr: value only
        if name == "ticker":
            raise UnsupportedPythonError("ticker() must be a statement, not nested", node)
        if name in {"note", "folder", "end_folder", "viewport", "graph_settings", "table"}:
            raise UnsupportedPythonError(f"{name}() must be a statement, not nested", node)
        inner = ",".join(self.emit(a) for a in args)
        return rf"{func_to_latex(name)}\left({inner}\right)"

    def _math_call(self, node: ast.Call, name: str) -> str:
        if name == "sqrt":
            if len(node.args) != 1:
                raise UnsupportedPythonError("sqrt() takes one argument", node)
            return rf"\sqrt{{{self.emit(node.args[0])}}}"
        if name == "abs":
            if len(node.args) != 1:
                raise UnsupportedPythonError("abs() takes one argument", node)
            return rf"\left|{self.emit(node.args[0])}\right|"
        if name == "pow":
            if len(node.args) != 2:
                raise UnsupportedPythonError("pow() takes two arguments", node)
            base = self.emit(node.args[0])
            if not _is_atom(node.args[0]):
                base = rf"\left({base}\right)"
            return f"{base}^{{{self.emit(node.args[1])}}}"
        if name == "log":
            # Python: log(x) is ln; log(x, b) is log base b.
            if len(node.args) == 1:
                return rf"\ln\left({self.emit(node.args[0])}\right)"
            if len(node.args) == 2:
                base = self.emit(node.args[1])
                return rf"\log_{{{base}}}\left({self.emit(node.args[0])}\right)"
            raise UnsupportedPythonError("log() takes one or two arguments", node)
        if name == "len":
            if len(node.args) != 1:
                raise UnsupportedPythonError("len() takes one argument", node)
            return rf"\operatorname{{length}}\left({self.emit(node.args[0])}\right)"
        if name == "sum":
            return self._sum_or_prod(node, r"\sum")
        if name == "prod":
            return self._sum_or_prod(node, r"\prod")
        if name == "range":
            return range_to_latex(node.args, self)
        if name == "list":
            if len(node.args) == 1:
                return self.emit(node.args[0])
            raise UnsupportedPythonError("list() takes at most one argument", node)
        if name == "min" or name == "max":
            inner = ",".join(self.emit(a) for a in node.args)
            return rf"{LATEX_FUNCS[name]}\left({inner}\right)"
        if name == "round":
            inner = ",".join(self.emit(a) for a in node.args)
            return rf"\operatorname{{round}}\left({inner}\right)"
        if name in LATEX_FUNCS:
            inner = ",".join(self.emit(a) for a in node.args)
            return rf"{LATEX_FUNCS[name]}\left({inner}\right)"
        if name in OPERATORNAME_FUNCS:
            inner = ",".join(self.emit(a) for a in node.args)
            return rf"\operatorname{{{name}}}\left({inner}\right)"
        # User-defined function.
        callee = ident_to_latex(name)
        inner = ",".join(self.emit(a) for a in node.args)
        return rf"{callee}\left({inner}\right)"

    def _attribute_call(self, node: ast.Call) -> str:
        func = node.func
        assert isinstance(func, ast.Attribute)
        if isinstance(func.value, ast.Name) and func.value.id in {"math", "np"}:
            return self._math_call(node, func.attr)
        raise UnsupportedPythonError(
            f"method call {_unparse(func)} is not supported", node
        )

    def _sum_or_prod(self, node: ast.Call, op: str) -> str:
        if not node.args:
            raise UnsupportedPythonError(f"{op} needs an argument", node)
        arg = node.args[0]
        if isinstance(arg, ast.GeneratorExp):
            if len(arg.generators) != 1:
                raise UnsupportedPythonError("only one generator is supported", arg)
            gen = arg.generators[0]
            if gen.ifs:
                raise UnsupportedPythonError(
                    "comprehension filters in sum/prod are not supported", arg
                )
            target = gen.target
            if not isinstance(target, ast.Name):
                raise UnsupportedPythonError("sum/prod index must be a name", target)
            index = ident_to_latex(target.id)
            lo, hi = _sequence_bounds(gen.iter, self)
            body = self.emit(arg.elt)
            return rf"{op}_{{{index}={lo}}}^{{{hi}}}{body}"
        # sum(L) → total(L)
        if op == r"\sum":
            return rf"\operatorname{{total}}\left({self.emit(arg)}\right)"
        return rf"\prod\left({self.emit(arg)}\right)"

    def _comprehension(
        self,
        elt: ast.AST,
        generators: list[ast.comprehension],
        origin: ast.AST,
    ) -> str:
        if len(generators) != 1:
            raise UnsupportedPythonError(
                "nested comprehensions are not supported; flatten them", origin
            )
        gen = generators[0]
        if gen.is_async:
            raise UnsupportedPythonError("async comprehensions are not supported", origin)
        if not isinstance(gen.target, ast.Name):
            raise UnsupportedPythonError(
                "comprehension target must be a single name", gen.target
            )
        var = ident_to_latex(gen.target.id)
        body = self.emit(elt)
        iterable = _iterable_latex(gen.iter, self)
        extra = ""
        if gen.ifs:
            conds = ",".join(self.emit(c) for c in gen.ifs)
            extra = rf"\left\{{{conds}\right\}}"
        return rf"\left[{body}\operatorname{{for}}{var}={iterable}{extra}\right]"

    def _slice(self, value: str, sl: ast.Slice) -> str:
        if sl.step is not None:
            raise UnsupportedPythonError("slice steps are not supported", sl)
        if sl.lower is None and sl.upper is None:
            return value
        if sl.lower is None or sl.upper is None:
            raise UnsupportedPythonError(
                "Desmos list slices need both ends (L[a:b] → L[a...b-1])", sl
            )
        lo = LatexVisitor(self.source).emit(sl.lower)
        hi = LatexVisitor(self.source).emit(sl.upper)
        # Python is exclusive-end; Desmos [a...b] is inclusive.
        return rf"{value}\left[{lo}...{hi}-1\right]"

    def _multiply(
        self, left_node: ast.AST, right_node: ast.AST, left: str, right: str
    ) -> str:
        if not _is_atom(left_node) and not isinstance(left_node, (ast.UnaryOp, ast.BinOp)):
            left = rf"\left({left}\right)"
        elif isinstance(left_node, ast.BinOp) and isinstance(
            left_node.op, (ast.Add, ast.Sub)
        ):
            left = rf"\left({left}\right)"
        if not _is_atom(right_node) and not isinstance(right_node, ast.BinOp):
            if not (
                isinstance(right_node, ast.UnaryOp) and isinstance(right_node.op, ast.USub)
            ):
                right = rf"\left({right}\right)"
        elif isinstance(right_node, ast.BinOp) and isinstance(
            right_node.op, (ast.Add, ast.Sub)
        ):
            right = rf"\left({right}\right)"
        if _is_numeric_constant(left_node) and isinstance(right_node, ast.Name):
            return f"{left}{right}"
        return rf"{left}\cdot{{{right}}}"

    def _not(self, operand: ast.AST) -> str:
        if isinstance(operand, ast.Compare) and len(operand.ops) == 1:
            negated = ast.Compare(
                left=operand.left,
                ops=[_negate_cmp(operand.ops[0])],
                comparators=operand.comparators,
            )
            ast.copy_location(negated, operand)
            return self.emit(negated)
        inner = self.emit(operand)
        return rf"\left\{{{inner}:0,1\right\}}"


def _cmp_op(op: ast.cmpop, _right: ast.AST) -> str:
    if isinstance(op, ast.Eq):
        return "="
    if isinstance(op, ast.NotEq):
        return r"\ne{}"
    if isinstance(op, ast.Lt):
        return "<"
    if isinstance(op, ast.LtE):
        return r"\le{}"
    if isinstance(op, ast.Gt):
        return ">"
    if isinstance(op, ast.GtE):
        return r"\ge{}"
    raise UnsupportedPythonError(
        f"comparison {type(op).__name__} is not supported in Desmos"
    )


def _negate_cmp(op: ast.cmpop) -> ast.cmpop:
    mapping = {
        ast.Eq: ast.NotEq(),
        ast.NotEq: ast.Eq(),
        ast.Lt: ast.GtE(),
        ast.LtE: ast.Gt(),
        ast.Gt: ast.LtE(),
        ast.GtE: ast.Lt(),
    }
    if type(op) not in mapping:
        raise UnsupportedPythonError(f"cannot negate comparison {type(op).__name__}")
    return mapping[type(op)]


def _is_atom(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _is_atom(node.operand)
    if isinstance(node, (ast.List, ast.Tuple, ast.Subscript, ast.Call)):
        return True
    return False


def _is_numeric_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float))


def _needs_paren_on_right_of_sub(node: ast.AST) -> bool:
    return isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub))


def _call_name(node: ast.Call) -> Optional[str]:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id in {"math", "np", "pydesmos"}:
            return func.attr
    return None


def _is_helper_call(node: ast.Call) -> bool:
    name = _call_name(node)
    return name in HELPER_NAMES if name else False


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return type(node).__name__


def _replace_ident(latex: str, ident: str, replacement: str) -> str:
    """Replace a standalone identifier token in already-emitted latex.

    ``t`` as parametric dummy is rewritten to ``\\theta`` for polar curves.
    We only replace when ``ident`` is a single letter that appears as itself
    (not as part of a command).
    """
    if len(ident) != 1:
        return latex
    out: list[str] = []
    i = 0
    while i < len(latex):
        ch = latex[i]
        if ch == ident and (i == 0 or not latex[i - 1].isalpha()) and (
            i + 1 == len(latex) or not latex[i + 1].isalpha()
        ):
            out.append(replacement)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def range_to_latex(args: Sequence[ast.AST], visitor: LatexVisitor) -> str:
    """Map Python ``range`` (exclusive end) to a Desmos inclusive list."""
    if not args or len(args) > 3:
        raise UnsupportedPythonError("range() takes 1 to 3 arguments")
    consts = [_const_int(a) for a in args]
    if all(c is not None for c in consts):
        ints = [int(c) for c in consts if c is not None]
        if len(ints) == 1:
            start, stop, step = 0, ints[0], 1
        elif len(ints) == 2:
            start, stop, step = ints[0], ints[1], 1
        else:
            start, stop, step = ints[0], ints[1], ints[2]
        return _closed_range_latex(start, stop, step)
    if len(args) == 1:
        return rf"\left[0...{_exclusive_stop(args[0], visitor)}\right]"
    if len(args) == 2:
        a = visitor.emit(args[0])
        b = _exclusive_stop(args[1], visitor)
        return rf"\left[{a}...{b}\right]"
    a = visitor.emit(args[0])
    b = visitor.emit(args[1])
    s = visitor.emit(args[2])
    return rf"\left[{a},{a}+{s}...{b}-{s}\right]"


def _exclusive_stop(node: ast.AST, visitor: LatexVisitor) -> str:
    """Convert a Python exclusive ``range`` stop into an inclusive Desmos bound.

    ``range(1, n+1)`` becomes ``[1...n]`` rather than ``[1...n+1-1]``.
    """
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        if isinstance(node.right, ast.Constant) and node.right.value == 1:
            return visitor.emit(node.left)
        if isinstance(node.left, ast.Constant) and node.left.value == 1:
            return visitor.emit(node.right)
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return str(node.value - 1)
    return rf"{visitor.emit(node)}-1"


def _closed_range_latex(start: int, stop: int, step: int) -> str:
    if step == 0:
        raise UnsupportedPythonError("range() step must not be 0")
    values = list(range(start, stop, step))
    if not values:
        return r"\left[\right]"
    if step == 1 and values[-1] >= start:
        return rf"\left[{start}...{values[-1]}\right]"
    if step == -1:
        return rf"\left[{start}...{values[-1]}\right]"
    if len(values) == 1:
        return rf"\left[{values[0]}\right]"
    if len(values) == 2:
        return rf"\left[{values[0]},{values[1]}\right]"
    return rf"\left[{values[0]},{values[1]}...{values[-1]}\right]"


def _const_int(node: ast.AST) -> Optional[int]:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _const_int(node.operand)
        return None if inner is None else -inner
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(
        node.value, bool
    ):
        return node.value
    return None


def _iterable_latex(node: ast.AST, visitor: LatexVisitor) -> str:
    if isinstance(node, ast.Call) and _call_name(node) == "range":
        return range_to_latex(node.args, visitor)
    if isinstance(node, ast.Call) and _call_name(node) == "list":
        if node.args:
            return _iterable_latex(node.args[0], visitor)
    return visitor.emit(node)


def _sequence_bounds(iter_node: ast.AST, visitor: LatexVisitor) -> tuple[str, str]:
    """Inclusive [lo, hi] for sum/prod indices from a range or list."""
    if isinstance(iter_node, ast.Call) and _call_name(iter_node) == "range":
        args = iter_node.args
        consts = [_const_int(a) for a in args]
        if all(c is not None for c in consts):
            ints = [int(c) for c in consts if c is not None]
            if len(ints) == 1:
                start, stop, step = 0, ints[0], 1
            elif len(ints) == 2:
                start, stop, step = ints[0], ints[1], 1
            else:
                start, stop, step = ints[0], ints[1], ints[2]
            if step != 1:
                raise UnsupportedPythonError(
                    "sum/prod over a strided range is not mapped; use a list",
                    iter_node,
                )
            last = stop - 1
            return str(start), str(last)
        if len(args) == 1:
            return "0", _exclusive_stop(args[0], visitor)
        if len(args) == 2:
            return visitor.emit(args[0]), _exclusive_stop(args[1], visitor)
        raise UnsupportedPythonError("sum/prod over a 3-arg range is not mapped", iter_node)
    # Fallback: 1 to length(L)
    latex = visitor.emit(iter_node)
    return "1", rf"\operatorname{{length}}\left({latex}\right)"


def circle_latex(
    args: Sequence[ast.AST],
    *,
    fill: bool,
    visitor: LatexVisitor,
) -> str:
    """``(x-h)^2+(y-k)^2 = r^2`` or ``\\le`` when filled."""
    if len(args) == 1:
        radius = visitor.emit(args[0])
        h, k = "0", "0"
    elif len(args) == 2:
        center = args[0]
        radius = visitor.emit(args[1])
        if isinstance(center, ast.Tuple) and len(center.elts) == 2:
            h = visitor.emit(center.elts[0])
            k = visitor.emit(center.elts[1])
        else:
            # center as a point expression: use distance
            c = visitor.emit(center)
            op = r"\le{}" if fill else "="
            return rf"\operatorname{{distance}}\left(\left(x,y\right),{c}\right){op}{radius}"
    else:
        raise UnsupportedPythonError("circle() takes (center, radius) or (radius)")
    op = r"\le{}" if fill else "="
    hx = "x" if h == "0" else rf"\left(x-{h}\right)"
    ky = "y" if k == "0" else rf"\left(y-{k}\right)"
    if h == "0":
        hx = "x"
    if k == "0":
        ky = "y"
    return rf"{hx}^{{2}}+{ky}^{{2}}{op}{radius}^{{2}}"


def sphere_latex(args: Sequence[ast.AST], visitor: LatexVisitor) -> str:
    if len(args) == 1:
        radius = visitor.emit(args[0])
        return rf"x^{{2}}+y^{{2}}+z^{{2}}={radius}^{{2}}"
    if len(args) == 2:
        center = args[0]
        radius = visitor.emit(args[1])
        if isinstance(center, ast.Tuple) and len(center.elts) == 3:
            h, k, m = (visitor.emit(e) for e in center.elts)
            def _term(var: str, offset: str) -> str:
                if offset == "0":
                    return rf"{var}^{{2}}"
                return rf"\left({var}-{offset}\right)^{{2}}"
            return rf"{_term('x', h)}+{_term('y', k)}+{_term('z', m)}={radius}^{{2}}"
        c = visitor.emit(center)
        return rf"\operatorname{{distance}}\left(\left(x,y,z\right),{c}\right)={radius}"
    raise UnsupportedPythonError("sphere() takes (radius) or (center, radius)")


def piecewise_latex(branches: list[tuple[Optional[str], str]]) -> str:
    """Build ``\\left\\{cond:val, cond:val, default\\right\\}``.

    Each branch is ``(condition_or_None, value)``. A ``None`` condition is the
    final default (Desmos omits the last condition).
    """
    if not branches:
        raise UnsupportedPythonError("piecewise needs at least one branch")
    parts: list[str] = []
    for cond, value in branches:
        if cond:
            parts.append(f"{cond}:{value}")
        else:
            parts.append(value)
    return rf"\left\{{{','.join(parts)}\right\}}"


def action_arrow(target: str, value: str) -> str:
    """Desmos action ``target \\to value``."""
    return rf"{target}\to{{{value}}}"


def action_latex_from_call(node: ast.Call, visitor: LatexVisitor) -> str:
    """``action(n, n+1)`` or ``action(score=score+1, lives=lives-1)``."""
    bits: list[str] = []
    if len(node.args) == 2 and not node.keywords:
        bits.append(action_arrow(_target_latex(node.args[0], visitor), visitor.emit(node.args[1])))
    elif len(node.args) == 1 and not node.keywords:
        bits.append(visitor.emit(node.args[0]))
    elif node.keywords and not node.args:
        for kw in node.keywords:
            if kw.arg is None:
                raise UnsupportedPythonError("**kwargs in action() is not supported", node)
            bits.append(action_arrow(ident_to_latex(kw.arg), visitor.emit(kw.value)))
    elif len(node.args) >= 1 and node.keywords:
        if len(node.args) == 2:
            bits.append(
                action_arrow(_target_latex(node.args[0], visitor), visitor.emit(node.args[1]))
            )
        elif len(node.args) == 1:
            bits.append(visitor.emit(node.args[0]))
        else:
            raise UnsupportedPythonError("unrecognized action() arguments", node)
        for kw in node.keywords:
            if kw.arg in {"on_click", "interval", "playing"}:
                continue
            if kw.arg is None:
                continue
            bits.append(action_arrow(ident_to_latex(kw.arg), visitor.emit(kw.value)))
    else:
        raise UnsupportedPythonError(
            "action() expected action(var, value) or action(var=value, ...)", node
        )
    if not bits:
        raise UnsupportedPythonError("action() produced no update rules", node)
    if len(bits) == 1:
        return bits[0]
    return rf"\left({','.join(bits)}\right)"


def assign_latex_from_call(node: ast.Call, visitor: LatexVisitor) -> str:
    if len(node.args) != 2:
        raise UnsupportedPythonError("assign(var, value) needs two arguments", node)
    return action_arrow(_target_latex(node.args[0], visitor), visitor.emit(node.args[1]))


def _target_latex(node: ast.AST, visitor: LatexVisitor) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return ident_to_latex(node.value)
    if isinstance(node, ast.Name):
        return ident_to_latex(node.id)
    return visitor.emit(node)


def function_lhs(name: str, args: Sequence[str]) -> str:
    params = ",".join(ident_to_latex(a) for a in args)
    return rf"{ident_to_latex(name)}\left({params}\right)"


def with_substitution(expr: str, bindings: list[tuple[str, str]]) -> str:
    if not bindings:
        return expr
    inner = ",".join(f"{n}={v}" for n, v in bindings)
    return rf"{expr}\operatorname{{with}}{inner}"
