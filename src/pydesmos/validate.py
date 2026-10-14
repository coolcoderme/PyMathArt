"""Lightweight structural validation of Desmos graph-state objects."""

from __future__ import annotations

from typing import Any, Iterable

from pydesmos.errors import GraphStateError

ITEM_TYPES = {"expression", "text", "folder", "table", "image"}
LINE_STYLES = {"SOLID", "DASHED", "DOTTED"}
POINT_STYLES = {"POINT", "OPEN", "CROSS"}


def validate_state(state: dict[str, Any]) -> dict[str, Any]:
    """Raise ``GraphStateError`` if ``state`` cannot be a Desmos setState payload.

    This does not parse LaTeX the way Desmos does; it checks the JSON envelope
    that ``Calc.setState`` expects (version, graph.viewport, expressions.list).
    """
    if not isinstance(state, dict):
        raise GraphStateError("graph state must be a JSON object")
    if "version" not in state:
        raise GraphStateError("graph state missing 'version'")
    if not isinstance(state["version"], int):
        raise GraphStateError("graph state 'version' must be an integer")
    graph = state.get("graph")
    if not isinstance(graph, dict):
        raise GraphStateError("graph state missing 'graph' object")
    viewport = graph.get("viewport")
    if not isinstance(viewport, dict):
        raise GraphStateError("graph.viewport is required")
    for key in ("xmin", "xmax", "ymin", "ymax"):
        if key not in viewport:
            raise GraphStateError(f"graph.viewport missing '{key}'")
        if not isinstance(viewport[key], (int, float)):
            raise GraphStateError(f"graph.viewport.{key} must be a number")
    expressions = state.get("expressions")
    if not isinstance(expressions, dict):
        raise GraphStateError("graph state missing 'expressions' object")
    items = expressions.get("list")
    if not isinstance(items, list):
        raise GraphStateError("expressions.list must be an array")
    ids: set[str] = set()
    for i, item in enumerate(items):
        _validate_item(item, i, ids)
    ticker = expressions.get("ticker")
    if ticker is not None:
        if not isinstance(ticker, dict):
            raise GraphStateError("expressions.ticker must be an object")
        if "handlerLatex" in ticker and not isinstance(ticker["handlerLatex"], str):
            raise GraphStateError("ticker.handlerLatex must be a string")
    return state


def _validate_item(item: Any, index: int, ids: set[str]) -> None:
    if not isinstance(item, dict):
        raise GraphStateError(f"expressions.list[{index}] must be an object")
    itype = item.get("type")
    if itype not in ITEM_TYPES:
        raise GraphStateError(
            f"expressions.list[{index}] has unknown type {itype!r}"
        )
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id:
        raise GraphStateError(f"expressions.list[{index}] needs a string id")
    if item_id in ids:
        raise GraphStateError(f"duplicate expression id {item_id!r}")
    ids.add(item_id)
    if itype == "expression":
        latex = item.get("latex")
        if latex is None:
            raise GraphStateError(f"expression {item_id!r} missing latex")
        if not isinstance(latex, str):
            raise GraphStateError(f"expression {item_id!r} latex must be a string")
        _check_braces(latex, item_id)
        if "lineStyle" in item and item["lineStyle"] not in LINE_STYLES:
            raise GraphStateError(
                f"expression {item_id!r} has invalid lineStyle {item['lineStyle']!r}"
            )
        if "pointStyle" in item and item["pointStyle"] not in POINT_STYLES:
            raise GraphStateError(
                f"expression {item_id!r} has invalid pointStyle {item['pointStyle']!r}"
            )
        click = item.get("clickableInfo")
        if click is not None:
            if not isinstance(click, dict):
                raise GraphStateError(f"expression {item_id!r} clickableInfo must be an object")
            if "latex" in click and not isinstance(click["latex"], str):
                raise GraphStateError(f"expression {item_id!r} clickableInfo.latex must be a string")
    elif itype == "text":
        if "text" in item and not isinstance(item["text"], str):
            raise GraphStateError(f"note {item_id!r} text must be a string")
    elif itype == "folder":
        if "title" in item and not isinstance(item["title"], str):
            raise GraphStateError(f"folder {item_id!r} title must be a string")
    elif itype == "table":
        cols = item.get("columns")
        if not isinstance(cols, list) or not cols:
            raise GraphStateError(f"table {item_id!r} needs a columns array")


def _check_braces(latex: str, item_id: str) -> None:
    depth = 0
    i = 0
    while i < len(latex):
        ch = latex[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                raise GraphStateError(f"expression {item_id!r} has unmatched '}}' in latex")
        i += 1
    if depth != 0:
        raise GraphStateError(f"expression {item_id!r} has unmatched '{{' in latex")
    if latex.count(r"\left") != latex.count(r"\right"):
        raise GraphStateError(
            f"expression {item_id!r} has unmatched \\left/\\right in latex"
        )


def latex_strings(state: dict[str, Any]) -> Iterable[str]:
    for item in state.get("expressions", {}).get("list", []):
        if item.get("type") == "expression" and "latex" in item:
            yield item["latex"]
        click = item.get("clickableInfo") or {}
        if "latex" in click:
            yield click["latex"]
    ticker = state.get("expressions", {}).get("ticker") or {}
    if "handlerLatex" in ticker:
        yield ticker["handlerLatex"]
