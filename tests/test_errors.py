from __future__ import annotations

import pytest

from pydesmos import UnsupportedPythonError, transpile


def test_class_rejected():
    with pytest.raises(UnsupportedPythonError, match="classes"):
        transpile("class Foo:\n    pass")


def test_while_rejected():
    with pytest.raises(UnsupportedPythonError, match="while"):
        transpile("while True:\n    x = 1")


def test_try_rejected():
    with pytest.raises(UnsupportedPythonError, match="try"):
        transpile("try:\n    a = 1\nexcept Exception:\n    pass")


def test_unknown_import_rejected():
    with pytest.raises(UnsupportedPythonError, match="numpy"):
        transpile("import numpy\na = 1")


def test_async_rejected():
    with pytest.raises(UnsupportedPythonError, match="async"):
        transpile("async def f():\n    return 1")


def test_module_level_if_rejected():
    with pytest.raises(UnsupportedPythonError, match="module-level if"):
        transpile("if True:\n    a = 1")


def test_error_includes_line_number():
    src = "a = 1\nwhile a:\n    a = 0"
    with pytest.raises(UnsupportedPythonError) as ei:
        transpile(src)
    assert ei.value.lineno == 2
    assert "line 2" in str(ei.value)


def test_empty_source_rejected():
    with pytest.raises(UnsupportedPythonError, match="no transpilable"):
        transpile("import math\n")


def test_walrus_rejected():
    with pytest.raises(UnsupportedPythonError):
        transpile("a = (x := 1)")


def test_for_loop_without_append_rejected():
    with pytest.raises(UnsupportedPythonError, match="append"):
        transpile("for i in range(3):\n    x = i")
