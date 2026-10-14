from __future__ import annotations

import ast

import pytest

from pydesmos.latex import to_latex
from pydesmos.names import ident_to_latex


def L(src: str) -> str:
    tree = ast.parse(src, mode="eval")
    return to_latex(tree.body)


def test_ident_single_letter():
    assert ident_to_latex("a") == "a"
    assert ident_to_latex("x") == "x"


def test_ident_subscripted():
    assert ident_to_latex("score") == r"s_{core}"
    assert ident_to_latex("a1") == r"a_{1}"
    assert ident_to_latex("lives") == r"l_{ives}"


def test_ident_greek_and_specials():
    assert ident_to_latex("theta") == r"\theta"
    assert ident_to_latex("pi") == r"\pi"
    assert ident_to_latex("dt") == r"\operatorname{dt}"
    assert ident_to_latex("index") == r"\operatorname{index}"


def test_arithmetic():
    assert L("1 + 2 * 3") == r"1+2\cdot{3}"
    assert L("x ** 2") == r"x^{2}"
    assert L("a / b") == r"\frac{a}{b}"
    assert L("2 * x") == "2x"
    assert L("-x") == "-x"
    assert L("x - y + 1") == "x-y+1"


def test_math_module_attr():
    assert L("math.sin(math.pi)") == r"\sin\left(\pi\right)"


def test_functions():
    assert L("sin(x)") == r"\sin\left(x\right)"
    assert L("sqrt(x + 1)") == r"\sqrt{x+1}"
    assert L("abs(x)") == r"\left|x\right|"
    assert L("log(x)") == r"\ln\left(x\right)"
    assert L("log10(x)") == r"\log\left(x\right)"
    assert L("log(x, 2)") == r"\log_{2}\left(x\right)"
    assert L("len(L)") == r"\operatorname{length}\left(L\right)"
    assert L("f(x, y)") == r"f\left(x,y\right)"


def test_lists_and_points():
    assert L("[1, 2, 3]") == r"\left[1,2,3\right]"
    assert L("(1, 2)") == r"\left(1,2\right)"
    assert L("(x, y, z)") == r"\left(x,y,z\right)"
    assert L("L[i]") == r"L\left[i\right]"


def test_range_and_comprehension():
    assert L("range(1, 11)") == r"\left[1...10\right]"
    assert L("range(10)") == r"\left[0...9\right]"
    assert L("range(0, 10, 2)") == r"\left[0,2...8\right]"
    assert L("[i ** 2 for i in range(1, 5)]") == (
        r"\left[i^{2}\operatorname{for}i=\left[1...4\right]\right]"
    )


def test_sum():
    assert L("sum(i ** 2 for i in range(1, n + 1))") == r"\sum_{i=1}^{n}i^{2}"
    assert L("sum(L)") == r"\operatorname{total}\left(L\right)"


def test_piecewise_ternary():
    assert L("x if x > 0 else -x") == r"\left\{x>0:x,-x\right\}"


def test_comparisons():
    assert L("x > 0") == "x>0"
    assert L("0 < x < 1") == r"0<x,x<1"
    assert L("a == b") == "a=b"
    assert L("a != b") == r"a\ne{}b"
    assert L("x >= 1") == r"x\ge{}1"


def test_boolean_and():
    assert L("x > 0 and y < 1") == "x>0,y<1"


def test_mod_floordiv():
    assert L("a % b") == r"\operatorname{mod}\left(a,b\right)"
    assert L("a // b") == r"\operatorname{floor}\left(\frac{a}{b}\right)"


def test_pi_and_e():
    assert L("2 * pi") == r"2\pi"
    assert L("e ** x") == r"e^{x}"


def test_tone_and_polygon():
    assert L("tone(440, 0.5)") == r"\operatorname{tone}\left(440,0.5\right)"
    assert L("polygon((0, 0), (1, 0), (0, 1))") == (
        r"\operatorname{polygon}\left(\left(0,0\right),\left(1,0\right),\left(0,1\right)\right)"
    )


def test_chained_pow():
    # Python: 2 ** 3 ** 2 is 2 ** (3 ** 2)
    assert L("2 ** 3 ** 2") == r"2^{3^{2}}"


    @pytest.mark.parametrize(
        "src",
        ["{1, 2}", "{x: 1}", "f'{x}'"],
    )
    def test_unsupported_literals(src: str):
        from pydesmos.errors import UnsupportedPythonError

        with pytest.raises(UnsupportedPythonError):
            L(src)


    def test_walrus_rejected_as_statement():
        from pydesmos.errors import UnsupportedPythonError
        from pydesmos import transpile

        with pytest.raises(UnsupportedPythonError):
            transpile("a = (x := 1)")
