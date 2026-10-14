"""Identifier and builtin mapping from Python names to Desmos LaTeX."""

from __future__ import annotations

import re

# Greek letters commonly typed as full names in Python.
GREEK: dict[str, str] = {
    "alpha": r"\alpha",
    "beta": r"\beta",
    "gamma": r"\gamma",
    "Gamma": r"\Gamma",
    "delta": r"\delta",
    "Delta": r"\Delta",
    "epsilon": r"\epsilon",
    "varepsilon": r"\varepsilon",
    "zeta": r"\zeta",
    "eta": r"\eta",
    "theta": r"\theta",
    "Theta": r"\Theta",
    "iota": r"\iota",
    "kappa": r"\kappa",
    "lam": r"\lambda",  # `lambda` is a Python keyword
    "lambda_": r"\lambda",
    "Lambda": r"\Lambda",
    "mu": r"\mu",
    "nu": r"\nu",
    "xi": r"\xi",
    "Xi": r"\Xi",
    "pi": r"\pi",
    "Pi": r"\Pi",
    "rho": r"\rho",
    "sigma": r"\sigma",
    "Sigma": r"\Sigma",
    "tau": r"\tau",
    "upsilon": r"\upsilon",
    "phi": r"\phi",
    "Phi": r"\Phi",
    "varphi": r"\varphi",
    "chi": r"\chi",
    "psi": r"\psi",
    "Psi": r"\Psi",
    "omega": r"\omega",
    "Omega": r"\Omega",
}

# Names that are a single Desmos token (not first-letter + subscript).
SPECIAL_IDENTS: dict[str, str] = {
    **GREEK,
    "dt": r"\operatorname{dt}",
    "index": r"\operatorname{index}",
    "inf": r"\infty",
    "infinity": r"\infty",
    "infty": r"\infty",
    "e": "e",
}

# Functions written with a leading backslash in Desmos LaTeX.
LATEX_FUNCS: dict[str, str] = {
    "sin": r"\sin",
    "cos": r"\cos",
    "tan": r"\tan",
    "cot": r"\cot",
    "sec": r"\sec",
    "csc": r"\csc",
    "arcsin": r"\arcsin",
    "arccos": r"\arccos",
    "arctan": r"\arctan",
    "arccot": r"\arccot",
    "arcsec": r"\arcsec",
    "arccsc": r"\arccsc",
    "sinh": r"\sinh",
    "cosh": r"\cosh",
    "tanh": r"\tanh",
    "ln": r"\ln",
    "log10": r"\log",
    "exp": r"\exp",
    "min": r"\min",
    "max": r"\max",
}

# Functions written \operatorname{name} in exported graph state.
OPERATORNAME_FUNCS: frozenset[str] = frozenset(
    {
        "floor",
        "ceil",
        "round",
        "sign",
        "mod",
        "gcd",
        "lcm",
        "abs",  # usually |x|, but abs of lists uses operatorname
        "mean",
        "median",
        "total",
        "length",
        "sort",
        "shuffle",
        "unique",
        "join",
        "nCr",
        "nPr",
        "stdev",
        "stdevp",
        "mad",
        "quantile",
        "polygon",
        "triangle",
        "distance",
        "midpoint",
        "rgb",
        "hsv",
        "tone",
        "random",
        "normalpdf",
        "normalcdf",
        "binompdf",
        "binomcdf",
        "invNorm",
        "invBinom",
        "pdf",
        "cdf",
        "erf",
        "nCr",
        "nPr",
        "for",
        "with",
        "count",
        "tscore",
        "tpdf",
        "tcdf",
        "invT",
        "poissondist",
        "binomialdist",
        "normaldist",
        "uniformdist",
        "tdist",
        "geodist",
        "spearman",
        "stats",
        "histogram",
        "dotplot",
        "boxplot",
        "itertest",
        "ttest",
        "ittest",
        "cov",
        "corr",
        "covp",
        "corrp",
        "det",
        "inv",
        "transpose",
        "rref",
        "rank",
        "trace",
        "identity",
        "sphere",
        "cube",
        "vector",
        "cross",
        "dot",
        "proj",
        "unitvector",
        "magnitude",
        "index",
        "dt",
    }
)

# Python names that should not be rewritten as first-letter subscripts.
KEEP_WHOLE: frozenset[str] = (
    frozenset(SPECIAL_IDENTS)
    | frozenset(LATEX_FUNCS)
    | OPERATORNAME_FUNCS
    | frozenset({"log", "sqrt", "pow", "sum", "prod", "len", "abs", "range", "list"})
)

HELPER_NAMES: frozenset[str] = frozenset(
    {
        "slider",
        "point",
        "point3d",
        "segment",
        "polygon",
        "circle",
        "parametric",
        "polar",
        "inequality",
        "tone",
        "ticker",
        "action",
        "assign",
        "note",
        "folder",
        "end_folder",
        "raw",
        "latex",
        "surface",
        "triangle",
        "sphere",
        "viewport",
        "rgb",
        "hsv",
        "clickable",
        "graph_settings",
        "table",
    }
)

_TRAILING_DIGITS = re.compile(r"^([A-Za-z])(\d+)$")
_VALID_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def ident_to_latex(name: str) -> str:
    """Convert a Python identifier to Desmos LaTeX.

    Desmos treats a run of letters as multiplication of single-letter
    variables, so multi-character Python names become a first letter plus
    a subscript: ``score`` → ``s_{core}``. Single letters, Greek names,
    and Desmos specials (``dt``, ``index``, ``pi``, …) are preserved.
    """
    if name in SPECIAL_IDENTS:
        return SPECIAL_IDENTS[name]
    if name in LATEX_FUNCS or name in OPERATORNAME_FUNCS:
        return func_to_latex(name)
    digits = _TRAILING_DIGITS.match(name)
    if digits:
        return f"{digits.group(1)}_{{{digits.group(2)}}}"
    if len(name) == 1:
        return name
    if name.startswith("_"):
        return name
    return f"{name[0]}_{{{name[1:]}}}"


def func_to_latex(name: str) -> str:
    """LaTeX for a function *name* used in call position."""
    if name in LATEX_FUNCS:
        return LATEX_FUNCS[name]
    if name in OPERATORNAME_FUNCS:
        return rf"\operatorname{{{name}}}"
    return ident_to_latex(name)


def is_valid_python_ident(name: str) -> bool:
    return bool(_VALID_IDENT.match(name))
