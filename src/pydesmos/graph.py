"""Programmatic Desmos graph builder and the object returned by ``transpile()``."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from pydesmos.html import render_html
from pydesmos.state import (
    GRAPH_STATE_VERSION,
    GraphSettings,
    IdFactory,
    Item,
    Target,
    TickerState,
    Viewport,
    build_state,
    color_for_index,
    expression_item,
    folder_item,
    text_item,
)
from pydesmos.style import Clickable, Domain, Slider, Style, normalize_color
from pydesmos.validate import validate_state

PathLike = Union[str, Path]


@dataclass
class Graph:
    """Accumulates expressions and serializes a Desmos graph state.

    Use either the Python-AST entry point (``transpile``) or these builder
    methods. Both produce the same JSON envelope that ``Calc.setState`` loads.
    """

    target: Target = "2d"
    viewport: Viewport = field(default_factory=Viewport)
    settings: GraphSettings = field(default_factory=GraphSettings)
    title: str = "pydesmos graph"
    random_seed: Optional[str] = None

    def __post_init__(self) -> None:
        self._ids = IdFactory()
        self._items: list[Item] = []
        self._ticker: Optional[TickerState] = None
        self._folder_id: Optional[str] = None
        self._color_index = 0
        self._plotted = 0

    # -- low-level ----------------------------------------------------------

    def add_expression(self, latex: str, style: Optional[Style] = None, **kwargs: Any) -> str:
        style = (style or Style()).apply_keywords(kwargs)
        if style.folder_id is None and self._folder_id:
            style.folder_id = self._folder_id
        item_id = kwargs.get("id") or self._ids.next()
        color_index = self._color_index
        item = expression_item(str(item_id), latex, style, color_index=color_index)
        self._items.append(item)
        self._color_index += 1
        self._plotted += 1
        return str(item_id)

    def add_note(self, text: str, **kwargs: Any) -> str:
        item_id = kwargs.get("id") or self._ids.next()
        folder = kwargs.get("folder_id", self._folder_id)
        self._items.append(text_item(str(item_id), text, folder_id=folder))
        return str(item_id)

    def add_folder(self, title: str, **kwargs: Any) -> str:
        item_id = kwargs.get("id") or self._ids.next()
        self._items.append(
            folder_item(
                str(item_id),
                title,
                collapsed=bool(kwargs.get("collapsed", False)),
                hidden=bool(kwargs.get("hidden", False)),
            )
        )
        self._folder_id = str(item_id)
        return str(item_id)

    def end_folder(self) -> None:
        self._folder_id = None

    def set_ticker(
        self,
        handler_latex: str,
        interval_ms: Union[str, int, float] = 16,
        *,
        playing: bool = False,
        open: bool = True,
    ) -> None:
        self._ticker = TickerState(
            handler_latex=handler_latex,
            min_step_latex=str(interval_ms),
            playing=playing,
            open=open,
        )

    def set_viewport(
        self,
        xmin: Optional[float] = None,
        xmax: Optional[float] = None,
        ymin: Optional[float] = None,
        ymax: Optional[float] = None,
        zmin: Optional[float] = None,
        zmax: Optional[float] = None,
    ) -> None:
        if xmin is not None:
            self.viewport.xmin = xmin
        if xmax is not None:
            self.viewport.xmax = xmax
        if ymin is not None:
            self.viewport.ymin = ymin
        if ymax is not None:
            self.viewport.ymax = ymax
        if zmin is not None:
            self.viewport.zmin = zmin
        if zmax is not None:
            self.viewport.zmax = zmax

    # -- convenience builders -----------------------------------------------

    def slider(
        self,
        name: str,
        value: Union[int, float, str],
        min: Union[int, float, str] = 0,
        max: Union[int, float, str] = 10,
        step: Optional[Union[int, float, str]] = None,
        **kwargs: Any,
    ) -> str:
        from pydesmos.names import ident_to_latex

        latex = f"{ident_to_latex(name)}={value}"
        style = Style(
            slider=Slider(
                min=str(min),
                max=str(max),
                step=None if step is None else str(step),
                playing=bool(kwargs.pop("playing", False)),
            )
        )
        return self.add_expression(latex, style, **kwargs)

    def note(self, text: str, **kwargs: Any) -> str:
        return self.add_note(text, **kwargs)

    def folder(self, title: str, **kwargs: Any) -> str:
        return self.add_folder(title, **kwargs)

    def expression(self, latex: str, **kwargs: Any) -> str:
        return self.add_expression(latex, **kwargs)

    def ticker(
        self,
        handler_latex: str,
        interval_ms: Union[str, int, float] = 16,
        **kwargs: Any,
    ) -> None:
        self.set_ticker(
            handler_latex,
            interval_ms,
            playing=bool(kwargs.get("playing", False)),
            open=bool(kwargs.get("open", True)),
        )

    # -- serialization ------------------------------------------------------

    @property
    def items(self) -> list[Item]:
        return list(self._items)

    def to_state(self, *, validate: bool = True) -> dict[str, Any]:
        state = build_state(
            self._items,
            target=self.target,
            viewport=self.viewport,
            settings=self.settings,
            ticker=self._ticker,
            random_seed=self.random_seed,
        )
        if validate:
            validate_state(state)
        return state

    def to_json(self, *, indent: Optional[int] = 2, validate: bool = True) -> str:
        return json.dumps(self.to_state(validate=validate), indent=indent, ensure_ascii=False)

    def to_html(self, **kwargs: Any) -> str:
        title = kwargs.pop("title", self.title)
        return render_html(self.to_state(), target=self.target, title=title, **kwargs)

    def save(self, path: PathLike, *, indent: Optional[int] = 2) -> Path:
        path = Path(path)
        path.write_text(self.to_json(indent=indent), encoding="utf-8")
        return path

    def save_html(self, path: PathLike, **kwargs: Any) -> Path:
        path = Path(path)
        path.write_text(self.to_html(**kwargs), encoding="utf-8")
        return path

    def save_all(self, json_path: PathLike, html_path: Optional[PathLike] = None) -> tuple[Path, Path]:
        json_path = Path(json_path)
        if html_path is None:
            html_path = json_path.with_suffix(".html")
        return self.save(json_path), self.save_html(html_path)

    def __len__(self) -> int:
        return len(self._items)


# Re-exports used by helpers / tests
__all__ = [
    "GRAPH_STATE_VERSION",
    "Graph",
    "GraphSettings",
    "Viewport",
    "Style",
    "Slider",
    "Domain",
    "Clickable",
    "color_for_index",
    "normalize_color",
]
