"""Errors raised while transpiling Python into Desmos."""

from __future__ import annotations

import ast
from typing import Optional


class PyDesmosError(Exception):
    """Base class for pydesmos errors."""


class UnsupportedPythonError(PyDesmosError):
    """A Python construct that has no Desmos equivalent (or is not mapped)."""

    def __init__(
        self,
        message: str,
        node: Optional[ast.AST] = None,
        *,
        lineno: Optional[int] = None,
        col_offset: Optional[int] = None,
    ) -> None:
        line = lineno
        col = col_offset
        if node is not None:
            line = getattr(node, "lineno", line)
            col = getattr(node, "col_offset", col)
        self.lineno = line
        self.col_offset = col
        self.node = node
        where = ""
        if line is not None:
            where = f" (line {line}"
            if col is not None:
                where += f", col {col + 1}"
            where += ")"
        super().__init__(f"Unsupported Python{where}: {message}")


class GraphStateError(PyDesmosError):
    """The produced or loaded graph state is not a valid Desmos state."""
