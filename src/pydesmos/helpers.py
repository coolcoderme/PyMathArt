"""Runtime helper functions recognized by the transpiler.

These exist so example modules and a programmatic ``Graph`` API can share
names. They are *not* evaluated during ``transpile()`` — the AST visitor
matches the call by name and emits Desmos LaTeX instead.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from pydesmos.graph import Graph
from pydesmos.names import ident_to_latex
from pydesmos.style import Slider, Style

Number = Union[int, float]


class Expr:
    """A tiny runtime stand-in so accidentally executing a DSL file does not
    crash on arithmetic. Transpile never uses this class."""

    def __init__(self, latex: str = "0") -> None:
        self.latex = latex

    def _bin(self, op: str, other: Any) -> "Expr":
        return Expr(f"({self.latex}{op}{other})")

    def __add__(self, other: Any) -> "Expr":
        return self._bin("+", other)

    def __radd__(self, other: Any) -> "Expr":
        return Expr(f"({other}+{self.latex})")

    def __sub__(self, other: Any) -> "Expr":
        return self._bin("-", other)

    def __rsub__(self, other: Any) -> "Expr":
        return Expr(f"({other}-{self.latex})")

    def __mul__(self, other: Any) -> "Expr":
        return self._bin("*", other)

    def __rmul__(self, other: Any) -> "Expr":
        return Expr(f"({other}*{self.latex})")

    def __truediv__(self, other: Any) -> "Expr":
        return self._bin("/", other)

    def __pow__(self, other: Any) -> "Expr":
        return Expr(f"({self.latex}**{other})")

    def __neg__(self) -> "Expr":
        return Expr(f"-({self.latex})")

    def __call__(self, *args: Any, **kwargs: Any) -> "Expr":
        return Expr(self.latex)

    def __repr__(self) -> str:
        return f"Expr({self.latex!r})"


def slider(
    value: Number,
    min: Number = 0,
    max: Number = 10,
    step: Optional[Number] = None,
    **kwargs: Any,
) -> Number:
    return value


def point(*coords: Any, **kwargs: Any) -> Expr:
    return Expr("point")


def point3d(*coords: Any, **kwargs: Any) -> Expr:
    return Expr("point3d")


def segment(a: Any, b: Any, **kwargs: Any) -> Expr:
    return Expr("segment")


def polygon(*points: Any, **kwargs: Any) -> Expr:
    return Expr("polygon")


def circle(center: Any, radius: Any = None, **kwargs: Any) -> Expr:
    return Expr("circle")


def parametric(*components: Any, **kwargs: Any) -> Expr:
    return Expr("parametric")


def polar(r: Any, **kwargs: Any) -> Expr:
    return Expr("polar")


def inequality(expr: Any, **kwargs: Any) -> Expr:
    return Expr("inequality")


def tone(frequency: Any, gain: Any = None, **kwargs: Any) -> Expr:
    return Expr("tone")


def ticker(action: Any, interval_ms: Number = 16, **kwargs: Any) -> None:
    return None


def action(*args: Any, **kwargs: Any) -> Expr:
    return Expr("action")


def assign(var: Any, value: Any) -> Expr:
    return Expr("assign")


def note(text: str, **kwargs: Any) -> None:
    return None


def folder(title: str, **kwargs: Any) -> None:
    return None


def end_folder() -> None:
    return None


def raw(latex: str, **kwargs: Any) -> str:
    return latex


def latex(latex_str: str, **kwargs: Any) -> str:
    return latex_str


def surface(expr: Any, **kwargs: Any) -> Expr:
    return Expr("surface")


def triangle(*points: Any, **kwargs: Any) -> Expr:
    return Expr("triangle")


def sphere(center: Any, radius: Any = None, **kwargs: Any) -> Expr:
    return Expr("sphere")


def viewport(**kwargs: Any) -> None:
    return None


def graph_settings(**kwargs: Any) -> None:
    return None


def rgb(r: Any, g: Any, b: Any) -> Expr:
    return Expr("rgb")


def hsv(h: Any, s: Any, v: Any) -> Expr:
    return Expr("hsv")


def clickable(on_click: Any, **kwargs: Any) -> Any:
    return on_click


# Names that are valid in the DSL without importing math. They evaluate to
# dummy Expr objects if someone runs the file as Python.
sin = Expr("sin")
cos = Expr("cos")
tan = Expr("tan")
asin = Expr("asin")
acos = Expr("acos")
atan = Expr("atan")
arcsin = Expr("arcsin")
arccos = Expr("arccos")
arctan = Expr("arctan")
sinh = Expr("sinh")
cosh = Expr("cosh")
tanh = Expr("tanh")
log = Expr("log")
ln = Expr("ln")
log10 = Expr("log10")
exp = Expr("exp")
sqrt = Expr("sqrt")
floor = Expr("floor")
ceil = Expr("ceil")
pi = 3.141592653589793
e = 2.718281828459045
tau = 6.283185307179586
inf = float("inf")

# Free variables that Desmos treats as coordinates / parameters. Provided so
# example files can be imported as ordinary Python without a NameError.
x = Expr("x")
y = Expr("y")
z = Expr("z")
t = Expr("t")
u = Expr("u")
v = Expr("v")
r = Expr("r")
theta = Expr("theta")


def graph_from_helpers() -> Graph:
    """Empty graph; used by tests for the programmatic API."""
    return Graph()


__all__ = [
    "Expr",
    "Graph",
    "Slider",
    "Style",
    "action",
    "assign",
    "circle",
    "clickable",
    "end_folder",
    "folder",
    "graph_settings",
    "hsv",
    "ident_to_latex",
    "inequality",
    "latex",
    "note",
    "parametric",
    "point",
    "point3d",
    "polar",
    "polygon",
    "raw",
    "rgb",
    "segment",
    "slider",
    "sphere",
    "surface",
    "ticker",
    "tone",
    "triangle",
    "viewport",
    "sin",
    "cos",
    "tan",
    "pi",
    "e",
    "tau",
]
