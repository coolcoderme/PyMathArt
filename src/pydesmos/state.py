"""Build a Desmos ``Calc.getState()`` / ``setState()`` JSON object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from pydesmos.style import DEFAULT_PALETTE, Style

# Live graphs on desmos.com currently serialize as version 11. The calculator
# migrates older versions on load; 11 is accepted by the v1.11–v1.13 APIs.
GRAPH_STATE_VERSION = 11

Target = Literal["2d", "3d"]


@dataclass
class Viewport:
    xmin: float = -10.0
    ymin: float = -10.0
    xmax: float = 10.0
    ymax: float = 10.0
    zmin: float = -5.0
    zmax: float = 5.0

    def to_2d(self) -> dict[str, float]:
        return {
            "xmin": self.xmin,
            "ymin": self.ymin,
            "xmax": self.xmax,
            "ymax": self.ymax,
        }

    def to_3d(self) -> dict[str, float]:
        data = self.to_2d()
        data["zmin"] = self.zmin
        data["zmax"] = self.zmax
        return data


@dataclass
class GraphSettings:
    show_grid: bool = True
    show_x_axis: bool = True
    show_y_axis: bool = True
    show_z_axis: bool = True
    x_axis_numbers: bool = True
    y_axis_numbers: bool = True
    polar_mode: bool = False
    degree_mode: bool = False
    square_axes: bool = True
    x_axis_label: str = ""
    y_axis_label: str = ""
    z_axis_label: str = ""
    polar_numbers: bool = True

    def to_2d(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "showGrid": self.show_grid,
            "showXAxis": self.show_x_axis,
            "showYAxis": self.show_y_axis,
            "xAxisNumbers": self.x_axis_numbers,
            "yAxisNumbers": self.y_axis_numbers,
            "polarNumbers": self.polar_numbers,
            "degreeMode": self.degree_mode,
            "polarMode": self.polar_mode,
            "squareAxes": self.square_axes,
        }
        if self.x_axis_label:
            data["xAxisLabel"] = self.x_axis_label
        if self.y_axis_label:
            data["yAxisLabel"] = self.y_axis_label
        return data

    def to_3d(self) -> dict[str, Any]:
        data = self.to_2d()
        data["showZAxis"] = self.show_z_axis
        if self.z_axis_label:
            data["zAxisLabel"] = self.z_axis_label
        return data


@dataclass
class TickerState:
    handler_latex: str
    min_step_latex: str = "16"
    open: bool = True
    playing: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "handlerLatex": self.handler_latex,
            "minStepLatex": str(self.min_step_latex),
            "open": self.open,
            "playing": self.playing,
        }


@dataclass
class Item:
    type: str
    id: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {"type": self.type, "id": self.id}
        data.update(self.payload)
        return data


class IdFactory:
    def __init__(self) -> None:
        self._n = 0

    def next(self) -> str:
        self._n += 1
        return str(self._n)

    @property
    def current(self) -> int:
        return self._n


def build_state(
    items: list[Item],
    *,
    target: Target = "2d",
    viewport: Optional[Viewport] = None,
    settings: Optional[GraphSettings] = None,
    ticker: Optional[TickerState] = None,
    random_seed: Optional[str] = None,
) -> dict[str, Any]:
    viewport = viewport or Viewport()
    settings = settings or GraphSettings()
    if target == "3d":
        # 3D calculator default cube is [-5, 5] on each axis.
        if viewport.xmin == -10.0 and viewport.xmax == 10.0:
            viewport = Viewport(
                xmin=-5.0,
                ymin=-5.0,
                xmax=5.0,
                ymax=5.0,
                zmin=viewport.zmin,
                zmax=viewport.zmax,
            )
        graph = settings.to_3d()
        graph["viewport"] = viewport.to_3d()
        # Identity-ish isometric rotation used by many saved 3D graphs.
        graph["axis3D"] = [0, 0, 1]
        graph["worldRotation3D"] = [
            -0.2938926261462366,
            -0.19134171618254492,
            -0.19134171618254486,
            0.9158907299982525,
        ]
    else:
        graph = settings.to_2d()
        graph["viewport"] = viewport.to_2d()

    expressions: dict[str, Any] = {"list": [item.to_dict() for item in items]}
    if ticker is not None:
        expressions["ticker"] = ticker.to_dict()

    state: dict[str, Any] = {
        "version": GRAPH_STATE_VERSION,
        "graph": graph,
        "expressions": expressions,
    }
    if random_seed:
        state["randomSeed"] = random_seed
    return state


def color_for_index(index: int) -> str:
    return DEFAULT_PALETTE[index % len(DEFAULT_PALETTE)]


def expression_item(
    item_id: str,
    latex: str,
    style: Optional[Style] = None,
    *,
    color_index: int = 0,
) -> Item:
    payload: dict[str, Any] = {"latex": latex, "color": color_for_index(color_index)}
    if style is not None:
        extra = style.to_expression_fields()
        payload.update(extra)
        if "color" not in extra:
            payload["color"] = color_for_index(color_index)
    return Item(type="expression", id=item_id, payload=payload)


def text_item(item_id: str, text: str, folder_id: Optional[str] = None) -> Item:
    payload: dict[str, Any] = {"text": text}
    if folder_id:
        payload["folderId"] = folder_id
    return Item(type="text", id=item_id, payload=payload)


def folder_item(
    item_id: str, title: str, *, collapsed: bool = False, hidden: bool = False
) -> Item:
    return Item(
        type="folder",
        id=item_id,
        payload={"title": title, "collapsed": collapsed, "hidden": hidden},
    )
