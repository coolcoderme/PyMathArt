"""Walk a Python AST and emit a Desmos ``Graph``."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any, Callable, Optional, Union

from pydesmos.errors import UnsupportedPythonError
from pydesmos.graph import Graph, GraphSettings, Viewport
from pydesmos.latex import (
    LatexVisitor,
    action_arrow,
    action_latex_from_call,
    assign_latex_from_call,
    circle_latex,
    function_lhs,
    piecewise_latex,
    sphere_latex,
    to_latex,
    with_substitution,
)
from pydesmos.names import HELPER_NAMES, ident_to_latex
from pydesmos.state import Target
from pydesmos.style import Clickable, Domain, Slider, Style

Source = Union[str, Path, ast.AST, Callable[..., Any]]

_SKIP_IF_MAIN = True


def transpile(
    source: Source,
    *,
    target: Optional[Target] = None,
    xmin: Optional[float] = None,
    xmax: Optional[float] = None,
    ymin: Optional[float] = None,
    ymax: Optional[float] = None,
    zmin: Optional[float] = None,
    zmax: Optional[float] = None,
    title: Optional[str] = None,
    filename: Optional[str] = None,
) -> Graph:
    """Transpile Python source into a Desmos graph.

    ``source`` may be a string of Python, a filesystem path, a parsed AST,
    or a function/callable (its source is extracted with ``inspect``).

    ``target`` is ``"2d"`` (graphing calculator) or ``"3d"``. If omitted,
    3D helpers such as ``surface()`` / ``sphere()`` / ``point3d()`` select 3D.
    """
    text, tree, name = _load_source(source, filename=filename)
    graph = Graph(target=target or "2d", title=title or name or "pydesmos graph")
    graph._target_explicit = target is not None  # type: ignore[attr-defined]
    if xmin is not None:
        graph.viewport.xmin = xmin
    if xmax is not None:
        graph.viewport.xmax = xmax
    if ymin is not None:
        graph.viewport.ymin = ymin
    if ymax is not None:
        graph.viewport.ymax = ymax
    if zmin is not None:
        graph.viewport.zmin = zmin
    if zmax is not None:
        graph.viewport.zmax = zmax
    visitor = Transpiler(graph, text)
    visitor.visit(tree)
    if not graph.items:
        raise UnsupportedPythonError("no transpilable statements found")
    if visitor.saw_3d and not getattr(graph, "_target_explicit", False):
        graph.target = "3d"
    return graph


def transpile_file(path: Union[str, Path], **kwargs: Any) -> Graph:
    path = Path(path)
    kwargs.setdefault("filename", str(path))
    kwargs.setdefault("title", path.stem.replace("_", " "))
    return transpile(path.read_text(encoding="utf-8"), **kwargs)


def _load_source(
    source: Source, filename: Optional[str]
) -> tuple[str, ast.AST, str]:
    if isinstance(source, Path) or (
        isinstance(source, str) and _looks_like_path(source)
    ):
        path = Path(source)
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        return text, tree, path.stem
    if isinstance(source, ast.AST):
        text = filename or "<ast>"
        return "", source, Path(filename).stem if filename else "graph"
    if callable(source) and not isinstance(source, type):
        import textwrap

        text = textwrap.dedent(inspect.getsource(source))
        tree = ast.parse(text)
        # If we were given a function, transpile its body.
        if (
            isinstance(tree, ast.Module)
            and len(tree.body) == 1
            and isinstance(tree.body[0], ast.FunctionDef)
        ):
            fn = tree.body[0]
            mod = ast.Module(body=fn.body, type_ignores=[])
            ast.fix_missing_locations(mod)
            return text, mod, fn.name
        return text, tree, getattr(source, "__name__", "graph")
    if isinstance(source, str):
        tree = ast.parse(source, filename=filename or "<string>")
        return source, tree, Path(filename).stem if filename else "graph"
    raise TypeError(f"cannot transpile {type(source).__name__}")


def _looks_like_path(source: str) -> bool:
    if "\n" in source or "\r" in source:
        return False
    p = Path(source)
    return p.suffix == ".py" and p.exists()


class Transpiler(ast.NodeVisitor):
    def __init__(self, graph: Graph, source: str) -> None:
        self.graph = graph
        self.source = source
        self.latex = LatexVisitor(source=source)
        self._pending_list: dict[str, str] = {}
        self.saw_3d = False

    # -- module / statements ------------------------------------------------

    def visit_Module(self, node: ast.Module) -> None:
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and _is_str_constant(node.body[0].value)
        ):
            doc = node.body[0].value.value  # type: ignore[attr-defined]
            if isinstance(doc, str) and doc.strip():
                self.graph.add_note(doc.strip().splitlines()[0])
            body = node.body[1:]
        else:
            body = node.body
        for stmt in body:
            self.visit(stmt)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name not in {"math", "pydesmos", "cmath"}:
                raise UnsupportedPythonError(
                    f"import {alias.name!r} is not available inside Desmos; "
                    "only math helpers and pydesmos helpers are recognized",
                    node,
                )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        if mod.split(".")[0] in {"pydesmos", "math", "cmath"}:
            return
        raise UnsupportedPythonError(
            f"from {mod} import ... is not available inside Desmos",
            node,
        )

    def visit_Expr(self, node: ast.Expr) -> None:
        value = node.value
        if _is_str_constant(value):
            text = value.value  # type: ignore[union-attr]
            if isinstance(text, str) and text.strip():
                self.graph.add_note(text.strip())
            return
        if isinstance(value, ast.Call) and _call_id(value) in HELPER_NAMES:
            self._helper_statement(value)
            return
        # Bare comparison / expression → plotted latex.
        self.graph.add_expression(self.latex.emit(value))

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) != 1:
            raise UnsupportedPythonError(
                "multiple assignment targets are not supported", node
            )
        self._assign(node.targets[0], node.value, node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is None:
            return
        self._assign(node.target, node.value, node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """``n += 1`` becomes the action ``n \\to n+1``."""
        target = self.latex.emit(node.target)
        op = node.op
        rhs = self.latex.emit(node.value)
        if isinstance(op, ast.Add):
            value = f"{target}+{rhs}"
        elif isinstance(op, ast.Sub):
            value = f"{target}-{rhs}"
        elif isinstance(op, ast.Mult):
            value = rf"{target}\cdot{{{rhs}}}"
        elif isinstance(op, ast.Div):
            value = rf"\frac{{{target}}}{{{rhs}}}"
        elif isinstance(op, ast.Pow):
            value = f"{target}^{{{rhs}}}"
        elif isinstance(op, ast.Mod):
            value = rf"\operatorname{{mod}}\left({target},{rhs}\right)"
        else:
            raise UnsupportedPythonError(
                f"augmented assignment {type(op).__name__} is not mapped to an action",
                node,
            )
        self.graph.add_expression(action_arrow(target, value))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.args.vararg or node.args.kwarg or node.args.kwonlyargs:
            raise UnsupportedPythonError(
                "Desmos functions only support positional parameters", node
            )
        if node.args.defaults:
            raise UnsupportedPythonError(
                "default parameter values are not supported", node
            )
        if node.decorator_list:
            # Allow a trivial passthrough; unknown decorators error.
            for dec in node.decorator_list:
                raise UnsupportedPythonError(
                    "function decorators are not mapped to Desmos", dec
                )
        params = [a.arg for a in node.args.args]
        lhs = function_lhs(node.name, params)
        rhs, style = self._function_body(node)
        self.graph.add_expression(f"{lhs}={rhs}", style)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        raise UnsupportedPythonError("async functions are not supported", node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        raise UnsupportedPythonError(
            "classes have no Desmos equivalent; use functions and assignments", node
        )

    def visit_For(self, node: ast.For) -> None:
        self._for_to_list(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        raise UnsupportedPythonError("async for is not supported", node)

    def visit_While(self, node: ast.While) -> None:
        raise UnsupportedPythonError(
            "while loops have no Desmos equivalent; use a ticker action or a list comprehension",
            node,
        )

    def visit_If(self, node: ast.If) -> None:
        if _is_main_guard(node):
            return
        raise UnsupportedPythonError(
            "module-level if/else is not mapped; put conditionals inside a "
            "function (they become piecewise) or use a ternary expression",
            node,
        )

    def visit_With(self, node: ast.With) -> None:
        raise UnsupportedPythonError("with-blocks are not supported", node)

    def visit_Try(self, node: ast.Try) -> None:
        raise UnsupportedPythonError("try/except is not supported", node)

    def visit_Raise(self, node: ast.Raise) -> None:
        raise UnsupportedPythonError("raise is not supported", node)

    def visit_Assert(self, node: ast.Assert) -> None:
        raise UnsupportedPythonError("assert is not supported", node)

    def visit_Delete(self, node: ast.Delete) -> None:
        raise UnsupportedPythonError("del is not supported", node)

    def visit_Pass(self, node: ast.Pass) -> None:
        return

    def visit_Break(self, node: ast.Break) -> None:
        raise UnsupportedPythonError("break is not supported", node)

    def visit_Continue(self, node: ast.Continue) -> None:
        raise UnsupportedPythonError("continue is not supported", node)

    def visit_Global(self, node: ast.Global) -> None:
        raise UnsupportedPythonError("global is not supported", node)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        raise UnsupportedPythonError("nonlocal is not supported", node)

    def visit_Return(self, node: ast.Return) -> None:
        raise UnsupportedPythonError("return is only valid inside a function", node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        raise UnsupportedPythonError("bare lambda is not a statement", node)

    def generic_visit(self, node: ast.AST) -> None:
        raise UnsupportedPythonError(
            f"{type(node).__name__} is not supported in a Desmos program", node
        )

    # -- assignment ---------------------------------------------------------

    def _assign(self, target: ast.AST, value: ast.AST, origin: ast.AST) -> None:
        if isinstance(target, ast.Tuple):
            if not isinstance(value, ast.Tuple) or len(target.elts) != len(value.elts):
                raise UnsupportedPythonError(
                    "unpacking assignment requires a tuple of the same length", origin
                )
            for t, v in zip(target.elts, value.elts):
                self._assign(t, v, origin)
            return
        if not isinstance(target, ast.Name):
            raise UnsupportedPythonError(
                "assignment target must be a name (or a tuple of names)", target
            )
        name = target.id
        lhs = ident_to_latex(name)

        if isinstance(value, ast.Lambda):
            params = [a.arg for a in value.args.args]
            rhs = self.latex.emit(value.body)
            self.graph.add_expression(f"{function_lhs(name, params)}={rhs}")
            return

        if isinstance(value, ast.Call) and _call_id(value) in HELPER_NAMES:
            self._helper_assignment(name, lhs, value)
            return

        # Empty list that a subsequent for-loop will fill.
        if isinstance(value, ast.List) and not value.elts:
            self._pending_list[name] = lhs
            return

        rhs = self.latex.emit(value)
        style = Style()
        self.graph.add_expression(f"{lhs}={rhs}", style)

    def _helper_assignment(self, py_name: str, lhs: str, call: ast.Call) -> None:
        helper = _call_id(call)
        assert helper is not None
        if helper in {"surface", "sphere", "point3d"}:
            self.saw_3d = True
        style = self._style_from_call(call)
        if helper == "slider":
            value, slider = self._parse_slider(call)
            style.slider = slider
            self.graph.add_expression(f"{lhs}={value}", style)
            return
        if helper in {"point", "point3d", "parametric", "polygon", "triangle", "segment"}:
            rhs = self.latex._helper_as_expr(call, helper)
            if helper == "segment":
                style.fill = False if style.fill is None else style.fill
                style.lines = True if style.lines is None else style.lines
            if helper == "polygon" and style.fill is None:
                style.fill = True
            self.graph.add_expression(f"{lhs}={rhs}", style)
            return
        if helper == "action":
            rhs = action_latex_from_call(call, self.latex)
            self.graph.add_expression(f"{lhs}={rhs}", style)
            return
        if helper == "assign":
            rhs = assign_latex_from_call(call, self.latex)
            self.graph.add_expression(f"{lhs}={rhs}", style)
            return
        if helper == "tone":
            rhs = self.latex._helper_as_expr(call, helper)
            self.graph.add_expression(f"{lhs}={rhs}", style)
            return
        if helper == "circle":
            fill = _kw_bool(call, "fill", False)
            rhs = circle_latex(call.args, fill=fill, visitor=self.latex)
            self.graph.add_expression(f"{lhs}={rhs}", style)
            return
        if helper == "polar":
            style = self._polar_style(call, style)
            return self._add_polar(lhs, call, style, bind=True)
        if helper in {"raw", "latex"}:
            rhs = self.latex._helper_as_expr(call, helper)
            self.graph.add_expression(f"{lhs}={rhs}" if "=" not in rhs else rhs, style)
            return
        if helper == "surface":
            rhs = self.latex.emit(call.args[0]) if call.args else ""
            self.graph.add_expression(f"{lhs}={rhs}", style)
            return
        rhs = self.latex._helper_as_expr(call, helper)
        self.graph.add_expression(f"{lhs}={rhs}", style)

    def _add_polar(self, lhs: str, call: ast.Call, style: Style, bind: bool) -> None:
        from pydesmos.latex import _replace_ident

        body = _replace_ident(self.latex.emit(call.args[0]), "t", r"\theta")
        if bind:
            self.graph.add_expression(f"{lhs}={body}", Style())
            self.graph.add_expression(rf"r={lhs}", style)
        else:
            self.graph.add_expression(rf"r={body}", style)

    # -- helper statements --------------------------------------------------

    def _helper_statement(self, call: ast.Call) -> None:
        helper = _call_id(call)
        assert helper is not None
        if helper in {"surface", "sphere", "point3d"}:
            self.saw_3d = True
        if helper == "parametric" and len(call.args) == 3:
            self.saw_3d = True
        if helper == "triangle" and len(call.args) >= 3:
            self.saw_3d = True
        style = self._style_from_call(call)
        if helper == "note":
            if not call.args:
                raise UnsupportedPythonError("note() needs a string", call)
            text = _string_arg(call.args[0], "note")
            self.graph.add_note(text)
            return
        if helper == "folder":
            if not call.args:
                raise UnsupportedPythonError("folder() needs a title", call)
            title = _string_arg(call.args[0], "folder")
            self.graph.add_folder(title)
            return
        if helper == "end_folder":
            self.graph.end_folder()
            return
        if helper == "viewport":
            self._viewport_call(call)
            return
        if helper == "graph_settings":
            self._settings_call(call)
            return
        if helper == "ticker":
            self._ticker_call(call)
            return
        if helper == "slider":
            raise UnsupportedPythonError(
                "slider() must be assigned to a name, e.g. a = slider(1, 0, 10)", call
            )
        if helper == "action":
            latex = action_latex_from_call(call, self.latex)
            self.graph.add_expression(latex, style)
            return
        if helper == "assign":
            latex = assign_latex_from_call(call, self.latex)
            self.graph.add_expression(latex, style)
            return
        if helper in {"raw", "latex"}:
            latex = self.latex._helper_as_expr(call, helper)
            self.graph.add_expression(latex, style)
            return
        if helper == "tone":
            latex = self.latex._helper_as_expr(call, helper)
            self.graph.add_expression(latex, style)
            return
        if helper == "polar":
            self._add_polar("", call, self._polar_style(call, style), bind=False)
            return
        if helper == "circle":
            fill = _kw_bool(call, "fill", False)
            latex = circle_latex(call.args, fill=fill, visitor=self.latex)
            if fill and style.fill is None:
                style.fill = True
            self.graph.add_expression(latex, style)
            return
        if helper == "sphere":
            latex = sphere_latex(call.args, visitor=self.latex)
            self.graph.add_expression(latex, style)
            return
        if helper == "surface":
            if not call.args:
                raise UnsupportedPythonError("surface() needs z(x, y)", call)
            latex = rf"z={self.latex.emit(call.args[0])}"
            self.graph.add_expression(latex, style)
            return
        if helper == "inequality":
            if not call.args:
                raise UnsupportedPythonError("inequality() needs an expression", call)
            self.graph.add_expression(self.latex.emit(call.args[0]), style)
            return
        if helper == "segment":
            latex = self.latex._helper_as_expr(call, helper)
            if style.fill is None:
                style.fill = False
            if style.lines is None:
                style.lines = True
            self.graph.add_expression(latex, style)
            return
        if helper == "polygon":
            latex = self.latex._helper_as_expr(call, helper)
            if style.fill is None:
                style.fill = True
            self.graph.add_expression(latex, style)
            return
        if helper in {"point", "point3d", "parametric", "triangle"}:
            latex = self.latex._helper_as_expr(call, helper)
            if helper == "parametric":
                style = self._parametric_style(call, style)
            self.graph.add_expression(latex, style)
            return
        if helper == "table":
            raise UnsupportedPythonError(
                "table() is reserved; build lists and points instead", call
            )
        # Fallback: emit as a math call.
        self.graph.add_expression(self.latex.emit(call), style)

    def _viewport_call(self, call: ast.Call) -> None:
        kwargs = _const_kwargs(call)
        self.graph.set_viewport(
            xmin=_opt_float(kwargs.get("xmin")),
            xmax=_opt_float(kwargs.get("xmax")),
            ymin=_opt_float(kwargs.get("ymin")),
            ymax=_opt_float(kwargs.get("ymax")),
            zmin=_opt_float(kwargs.get("zmin")),
            zmax=_opt_float(kwargs.get("zmax")),
        )

    def _settings_call(self, call: ast.Call) -> None:
        kwargs = _const_kwargs(call)
        s: GraphSettings = self.graph.settings
        if "polar" in kwargs or "polar_mode" in kwargs:
            s.polar_mode = bool(kwargs.get("polar", kwargs.get("polar_mode")))
        if "degrees" in kwargs or "degree_mode" in kwargs:
            s.degree_mode = bool(kwargs.get("degrees", kwargs.get("degree_mode")))
        if "grid" in kwargs:
            s.show_grid = bool(kwargs["grid"])
        if "x_axis" in kwargs:
            s.show_x_axis = bool(kwargs["x_axis"])
        if "y_axis" in kwargs:
            s.show_y_axis = bool(kwargs["y_axis"])
        if "z_axis" in kwargs:
            s.show_z_axis = bool(kwargs["z_axis"])
        if "x_label" in kwargs:
            s.x_axis_label = str(kwargs["x_label"])
        if "y_label" in kwargs:
            s.y_axis_label = str(kwargs["y_label"])

    def _ticker_call(self, call: ast.Call) -> None:
        if not call.args:
            raise UnsupportedPythonError(
                "ticker(action, interval_ms=16) needs an action", call
            )
        handler = call.args[0]
        if isinstance(handler, ast.Call) and _call_id(handler) in {"action", "assign"}:
            latex = self.latex.emit(handler)
        else:
            latex = self.latex.emit(handler)
        interval = "16"
        playing = False
        for kw in call.keywords:
            if kw.arg in {"interval", "interval_ms", "dt", "step"}:
                interval = self.latex.emit(kw.value)
            elif kw.arg == "playing":
                playing = _truthy_const(kw.value)
        if len(call.args) >= 2:
            interval = self.latex.emit(call.args[1])
        self.graph.set_ticker(latex, interval, playing=playing)

    def _parse_slider(self, call: ast.Call) -> tuple[str, Slider]:
        if not call.args:
            raise UnsupportedPythonError("slider() needs a current value", call)
        value = self.latex.emit(call.args[0])
        min_v = max_v = step = None
        playing = False
        if len(call.args) >= 2:
            min_v = self.latex.emit(call.args[1])
        if len(call.args) >= 3:
            max_v = self.latex.emit(call.args[2])
        if len(call.args) >= 4:
            step = self.latex.emit(call.args[3])
        for kw in call.keywords:
            if kw.arg == "min":
                min_v = self.latex.emit(kw.value)
            elif kw.arg == "max":
                max_v = self.latex.emit(kw.value)
            elif kw.arg == "step":
                step = self.latex.emit(kw.value)
            elif kw.arg == "playing":
                playing = _truthy_const(kw.value)
        return value, Slider(
            min=min_v if min_v is not None else "0",
            max=max_v if max_v is not None else "10",
            step=step,
            playing=playing,
        )

    def _style_from_call(self, call: ast.Call) -> Style:
        kwargs: dict[str, Any] = {}
        for kw in call.keywords:
            if kw.arg is None:
                continue
            if kw.arg in {"on_click", "click"}:
                kwargs["on_click"] = self._on_click_latex(kw.value)
                continue
            if kw.arg in {
                "t_min",
                "t_max",
                "theta_min",
                "theta_max",
                "u_min",
                "u_max",
                "v_min",
                "v_max",
            }:
                kwargs[kw.arg] = self.latex.emit(kw.value)
                continue
            if kw.arg in {"color_latex"}:
                kwargs["color_latex"] = self.latex.emit(kw.value)
                continue
            if isinstance(kw.value, ast.Call) and _call_id(kw.value) in {"rgb", "hsv"}:
                kwargs["color_latex"] = self.latex.emit(kw.value)
                continue
            if isinstance(kw.value, ast.Constant):
                kwargs[kw.arg] = kw.value.value
                continue
            # Style fields that are latex (line_width as expression, etc.)
            kwargs[kw.arg] = self.latex.emit(kw.value)
        return Style().apply_keywords(kwargs)

    def _on_click_latex(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Allow "n -> n+1" as a convenience; convert ASCII arrow.
            text = node.value.replace("->", r"\to{}").replace("→", r"\to{}")
            return text
        if isinstance(node, ast.Call) and _call_id(node) in {"action", "assign"}:
            return self.latex.emit(node)
        return self.latex.emit(node)

    def _polar_style(self, call: ast.Call, style: Style) -> Style:
        t_min = _kw_latex(call, "t_min", self.latex) or _kw_latex(
            call, "theta_min", self.latex
        )
        t_max = _kw_latex(call, "t_max", self.latex) or _kw_latex(
            call, "theta_max", self.latex
        )
        if t_min is None and t_max is None:
            style.polar_domain = Domain(min="0", max=r"2\pi")
        else:
            style.polar_domain = Domain(min=t_min or "0", max=t_max or r"2\pi")
        # Polar curves use polarDomain, not the parametric t-domain.
        style.parametric_domain = None
        return style

    def _parametric_style(self, call: ast.Call, style: Style) -> Style:
        t_min = _kw_latex(call, "t_min", self.latex)
        t_max = _kw_latex(call, "t_max", self.latex)
        if t_min is not None or t_max is not None:
            style.parametric_domain = Domain(min=t_min or "0", max=t_max or "1")
        elif style.parametric_domain is None and len(call.args) == 2:
            style.parametric_domain = Domain(min="0", max=r"2\pi")
        u_min = _kw_latex(call, "u_min", self.latex)
        u_max = _kw_latex(call, "u_max", self.latex)
        if u_min is not None or u_max is not None:
            style.parametric_domain = Domain(min=u_min or "0", max=u_max or "1")
        v_min = _kw_latex(call, "v_min", self.latex)
        v_max = _kw_latex(call, "v_max", self.latex)
        if v_min is not None or v_max is not None:
            style.domain = Domain(min=v_min or "0", max=v_max or "1")
        return style

    # -- functions / piecewise ----------------------------------------------

    def _function_body(self, node: ast.FunctionDef) -> tuple[str, Style]:
        body = [s for s in node.body if not isinstance(s, ast.Pass)]
        if (
            body
            and isinstance(body[0], ast.Expr)
            and _is_str_constant(body[0].value)
        ):
            body = body[1:]
        if not body:
            raise UnsupportedPythonError("function has no body", node)

        leading_assigns: list[tuple[str, str]] = []
        rest: list[ast.stmt] = []
        saw_non_assign = False
        for stmt in body:
            if not saw_non_assign and isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                t = stmt.targets[0]
                if isinstance(t, ast.Name):
                    leading_assigns.append(
                        (ident_to_latex(t.id), self.latex.emit(stmt.value))
                    )
                    continue
            saw_non_assign = True
            rest.append(stmt)

        rhs, style = self._block_to_expr(rest, node)
        rhs = with_substitution(rhs, leading_assigns)
        return rhs, style

    def _block_to_expr(self, body: list[ast.stmt], origin: ast.AST) -> tuple[str, Style]:
        if not body:
            raise UnsupportedPythonError("empty function body", origin)
        if len(body) == 1 and isinstance(body[0], ast.Return):
            if body[0].value is None:
                raise UnsupportedPythonError("return without a value", body[0])
            return self.latex.emit(body[0].value), Style()
        if len(body) == 1 and isinstance(body[0], ast.If):
            return self._if_to_piecewise(body[0]), Style()
        # All returns / ifs that we can fold into piecewise.
        if all(isinstance(s, (ast.Return, ast.If, ast.Pass)) for s in body):
            # Sequential returns after ifs: treat as if/else chain if we have one If.
            if len(body) == 2 and isinstance(body[0], ast.If) and isinstance(body[1], ast.Return):
                if_node = body[0]
                if not if_node.orelse:
                    if_node = ast.If(
                        test=if_node.test,
                        body=if_node.body,
                        orelse=[body[1]],
                    )
                    ast.copy_location(if_node, body[0])
                    return self._if_to_piecewise(if_node), Style()
            if len(body) == 1 and isinstance(body[0], ast.Return):
                return self.latex.emit(body[0].value), Style()  # type: ignore[arg-type]
        raise UnsupportedPythonError(
            "function bodies must be a single return, an if/elif/else of returns, "
            "or leading assignments followed by a return (mapped to Desmos `with`)",
            body[0],
        )

    def _if_to_piecewise(self, node: ast.If) -> str:
        branches: list[tuple[Optional[str], str]] = []
        current: Optional[ast.If] = node
        while current is not None:
            cond = self.latex.emit(current.test)
            value = self._return_block(current.body, current)
            branches.append((cond, value))
            orelse = current.orelse
            if not orelse:
                current = None
            elif len(orelse) == 1 and isinstance(orelse[0], ast.If):
                current = orelse[0]
            else:
                branches.append((None, self._return_block(orelse, orelse[0])))
                current = None
        return piecewise_latex(branches)

    def _return_block(self, body: list[ast.stmt], origin: ast.AST) -> str:
        stmts = [s for s in body if not isinstance(s, ast.Pass)]
        if len(stmts) == 1 and isinstance(stmts[0], ast.Return) and stmts[0].value is not None:
            return self.latex.emit(stmts[0].value)
        if len(stmts) == 1 and isinstance(stmts[0], ast.If):
            return self._if_to_piecewise(stmts[0])
        raise UnsupportedPythonError(
            "each branch of a piecewise function must return a single expression",
            origin,
        )

    # -- for-loops → lists --------------------------------------------------

    def _for_to_list(self, node: ast.For) -> None:
        """``xs = []; for i in range(n): xs.append(i**2)`` → list comprehension."""
        if node.orelse:
            raise UnsupportedPythonError("for/else is not supported", node)
        if not isinstance(node.target, ast.Name):
            raise UnsupportedPythonError("for-loop target must be a single name", node)
        if len(node.body) != 1:
            raise UnsupportedPythonError(
                "only a single append() in a for-loop is mapped to a Desmos list",
                node,
            )
        stmt = node.body[0]
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            raise UnsupportedPythonError(
                "for-loops must be of the form `xs.append(expr)` to become a list",
                stmt,
            )
        call = stmt.value
        if not (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "append"
            and isinstance(call.func.value, ast.Name)
        ):
            raise UnsupportedPythonError(
                "for-loops must be of the form `xs.append(expr)` to become a list",
                stmt,
            )
        list_name = call.func.value.id
        if list_name not in self._pending_list:
            raise UnsupportedPythonError(
                f"{list_name} must be assigned [] before a loop that appends to it",
                node,
            )
        if len(call.args) != 1:
            raise UnsupportedPythonError("append() takes one argument", call)
        elt = call.args[0]
        dummy = ast.ListComp(
            elt=elt,
            generators=[
                ast.comprehension(target=node.target, iter=node.iter, ifs=[], is_async=0)
            ],
        )
        ast.copy_location(dummy, node)
        lhs = self._pending_list.pop(list_name)
        rhs = self.latex.emit(dummy)
        self.graph.add_expression(f"{lhs}={rhs}")


def _call_id(call: ast.Call) -> Optional[str]:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
        if call.func.value.id in {"pydesmos", "math"}:
            return call.func.attr
    return None


def _is_str_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    names = {getattr(test.left, "id", None)} | {
        getattr(c, "id", None) for c in test.comparators if isinstance(c, ast.Name)
    }
    strs = [
        c.value
        for c in [test.left, *test.comparators]
        if isinstance(c, ast.Constant) and isinstance(c.value, str)
    ]
    return "__name__" in names and "__main__" in strs


def _string_arg(node: ast.AST, helper: str) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    raise UnsupportedPythonError(f"{helper}() requires a string literal")


def _kw_bool(call: ast.Call, name: str, default: bool) -> bool:
    for kw in call.keywords:
        if kw.arg == name:
            return _truthy_const(kw.value)
    return default


def _kw_latex(call: ast.Call, name: str, visitor: LatexVisitor) -> Optional[str]:
    for kw in call.keywords:
        if kw.arg == name:
            return visitor.emit(kw.value)
    return None


def _truthy_const(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return bool(node.value)
    raise UnsupportedPythonError("expected a boolean/constant literal", node)


def _const_kwargs(call: ast.Call) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for kw in call.keywords:
        if kw.arg is None:
            continue
        if isinstance(kw.value, ast.UnaryOp) and isinstance(kw.value.op, ast.USub):
            if isinstance(kw.value.operand, ast.Constant) and isinstance(
                kw.value.operand.value, (int, float)
            ):
                out[kw.arg] = -kw.value.operand.value
                continue
        if isinstance(kw.value, ast.Constant):
            out[kw.arg] = kw.value.value
        else:
            raise UnsupportedPythonError(
                f"{kw.arg}= must be a constant in this helper", kw.value
            )
    return out


def _opt_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)
