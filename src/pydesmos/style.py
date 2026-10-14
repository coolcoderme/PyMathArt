"""Plot style, slider, domain, and clickable metadata for an expression."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Optional, Union

from pydesmos.errors import UnsupportedPythonError

Color = str

LINE_STYLES = {"SOLID", "DASHED", "DOTTED"}
POINT_STYLES = {"POINT", "OPEN", "CROSS"}
DRAG_MODES = {"NONE", "X", "Y", "XY", "AUTO"}
LABEL_ORIENTATIONS = {
    "default",
    "center",
    "above",
    "below",
    "left",
    "right",
    "above_left",
    "above_right",
    "below_left",
    "below_right",
}

NAMED_COLORS: dict[str, str] = {
    "red": "#c74440",
    "blue": "#2d70b3",
    "green": "#388c46",
    "purple": "#6042a6",
    "orange": "#fa7e19",
    "black": "#000000",
    "white": "#ffffff",
    "gray": "#aaaaaa",
    "grey": "#aaaaaa",
    "pink": "#e377c2",
    "yellow": "#c4a000",
    "brown": "#8c6240",
}

DEFAULT_PALETTE = [
    "#c74440",
    "#2d70b3",
    "#388c46",
    "#6042a6",
    "#fa7e19",
    "#000000",
]


def normalize_color(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    key = value.strip()
    lower = key.lower()
    if lower in NAMED_COLORS:
        return NAMED_COLORS[lower]
    if key.startswith("#") and len(key) in {4, 7}:
        return key.lower() if len(key) == 7 else key
    if len(key) in {3, 6} and all(c in "0123456789abcdefABCDEF" for c in key):
        return f"#{key.lower()}"
    return key


def normalize_line_style(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.strip().upper()
    aliases = {"DASH": "DASHED", "DOT": "DOTTED", "SOLID": "SOLID"}
    v = aliases.get(v, v)
    if v not in LINE_STYLES:
        raise UnsupportedPythonError(f"unknown line_style {value!r}; use SOLID, DASHED, or DOTTED")
    return v


def normalize_point_style(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.strip().upper()
    aliases = {"OPEN": "OPEN", "CROSS": "CROSS", "POINT": "POINT", "CLOSED": "POINT"}
    v = aliases.get(v, v)
    if v not in POINT_STYLES:
        raise UnsupportedPythonError(f"unknown point_style {value!r}; use POINT, OPEN, or CROSS")
    return v


def normalize_drag_mode(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.strip().upper()
    if v not in DRAG_MODES:
        raise UnsupportedPythonError(f"unknown drag_mode {value!r}")
    return v


@dataclass
class Domain:
    min: str
    max: str

    def to_dict(self) -> dict[str, str]:
        return {"min": str(self.min), "max": str(self.max)}


@dataclass
class Slider:
    min: Optional[str] = None
    max: Optional[str] = None
    step: Optional[str] = None
    playing: bool = False
    hard_min: bool = True
    hard_max: bool = True
    animation_period: Optional[float] = None
    loop_mode: Optional[str] = None
    play_direction: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.min is not None:
            data["min"] = str(self.min)
            data["hardMin"] = self.hard_min
        if self.max is not None:
            data["max"] = str(self.max)
            data["hardMax"] = self.hard_max
        if self.step is not None:
            data["step"] = str(self.step)
        if self.playing:
            data["isPlaying"] = True
        if self.animation_period is not None:
            data["animationPeriod"] = self.animation_period
        if self.loop_mode is not None:
            data["loopMode"] = self.loop_mode
        if self.play_direction is not None:
            data["playDirection"] = self.play_direction
        return data


@dataclass
class Clickable:
    latex: str
    enabled: bool = True
    description: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"enabled": self.enabled, "latex": self.latex}
        if self.description:
            data["description"] = self.description
        return data


@dataclass
class Style:
    color: Optional[str] = None
    color_latex: Optional[str] = None
    line_style: Optional[str] = None
    line_width: Optional[Union[str, float, int]] = None
    line_opacity: Optional[Union[str, float, int]] = None
    point_style: Optional[str] = None
    point_size: Optional[Union[str, float, int]] = None
    point_opacity: Optional[Union[str, float, int]] = None
    fill: Optional[bool] = None
    fill_opacity: Optional[Union[str, float, int]] = None
    points: Optional[bool] = None
    lines: Optional[bool] = None
    hidden: Optional[bool] = None
    secret: Optional[bool] = None
    label: Optional[str] = None
    show_label: Optional[bool] = None
    label_size: Optional[str] = None
    label_orientation: Optional[str] = None
    drag_mode: Optional[str] = None
    parametric_domain: Optional[Domain] = None
    polar_domain: Optional[Domain] = None
    domain: Optional[Domain] = None
    slider: Optional[Slider] = None
    clickable: Optional[Clickable] = None
    folder_id: Optional[str] = None

    def merge(self, other: "Style") -> "Style":
        data = {}
        for f in fields(self):
            mine = getattr(self, f.name)
            theirs = getattr(other, f.name)
            data[f.name] = theirs if theirs is not None else mine
        return Style(**data)

    def apply_keywords(self, kwargs: dict[str, Any]) -> "Style":
        """Copy recognized style keys from a helper kwargs dict."""
        mapping = {
            "color": "color",
            "colour": "color",
            "color_latex": "color_latex",
            "line_style": "line_style",
            "linestyle": "line_style",
            "lineStyle": "line_style",
            "line_width": "line_width",
            "lineWidth": "line_width",
            "line_opacity": "line_opacity",
            "lineOpacity": "line_opacity",
            "opacity": "line_opacity",
            "point_style": "point_style",
            "pointStyle": "point_style",
            "point_size": "point_size",
            "pointSize": "point_size",
            "point_opacity": "point_opacity",
            "pointOpacity": "point_opacity",
            "fill": "fill",
            "fill_opacity": "fill_opacity",
            "fillOpacity": "fill_opacity",
            "points": "points",
            "lines": "lines",
            "hidden": "hidden",
            "secret": "secret",
            "label": "label",
            "show_label": "show_label",
            "showLabel": "show_label",
            "label_size": "label_size",
            "labelSize": "label_size",
            "label_orientation": "label_orientation",
            "labelOrientation": "label_orientation",
            "drag": "drag_mode",
            "drag_mode": "drag_mode",
            "dragMode": "drag_mode",
        }
        out = Style(
            color=self.color,
            color_latex=self.color_latex,
            line_style=self.line_style,
            line_width=self.line_width,
            line_opacity=self.line_opacity,
            point_style=self.point_style,
            point_size=self.point_size,
            point_opacity=self.point_opacity,
            fill=self.fill,
            fill_opacity=self.fill_opacity,
            points=self.points,
            lines=self.lines,
            hidden=self.hidden,
            secret=self.secret,
            label=self.label,
            show_label=self.show_label,
            label_size=self.label_size,
            label_orientation=self.label_orientation,
            drag_mode=self.drag_mode,
            parametric_domain=self.parametric_domain,
            polar_domain=self.polar_domain,
            domain=self.domain,
            slider=self.slider,
            clickable=self.clickable,
            folder_id=self.folder_id,
        )
        for key, attr in mapping.items():
            if key in kwargs and kwargs[key] is not None:
                value = kwargs[key]
                if attr == "color":
                    value = normalize_color(str(value))
                elif attr == "line_style":
                    value = normalize_line_style(str(value))
                elif attr == "point_style":
                    value = normalize_point_style(str(value))
                elif attr == "drag_mode":
                    value = normalize_drag_mode(str(value))
                setattr(out, attr, value)
        if out.label and out.show_label is None:
            out.show_label = True
        if "on_click" in kwargs and kwargs["on_click"] is not None:
            latex = kwargs["on_click"]
            desc = kwargs.get("click_description") or kwargs.get("description")
            out.clickable = Clickable(latex=str(latex), description=desc)
        if "parametric_domain" in kwargs and kwargs["parametric_domain"] is not None:
            out.parametric_domain = _as_domain(kwargs["parametric_domain"])
        if "polar_domain" in kwargs and kwargs["polar_domain"] is not None:
            out.polar_domain = _as_domain(kwargs["polar_domain"])
        if "domain" in kwargs and kwargs["domain"] is not None:
            out.domain = _as_domain(kwargs["domain"])
        t_min = kwargs.get("t_min", kwargs.get("umin", kwargs.get("min")))
        t_max = kwargs.get("t_max", kwargs.get("umax", kwargs.get("max")))
        # Only treat min/max as a parametric domain when they were not slider bounds.
        if kwargs.get("t_min") is not None or kwargs.get("t_max") is not None:
            out.parametric_domain = Domain(
                min=str(kwargs.get("t_min", "0")),
                max=str(kwargs.get("t_max", "1")),
            )
        if kwargs.get("theta_min") is not None or kwargs.get("theta_max") is not None:
            out.polar_domain = Domain(
                min=str(kwargs.get("theta_min", "0")),
                max=str(kwargs.get("theta_max", r"2\pi")),
            )
        if kwargs.get("u_min") is not None or kwargs.get("u_max") is not None:
            out.parametric_domain = Domain(
                min=str(kwargs.get("u_min", "0")),
                max=str(kwargs.get("u_max", "1")),
            )
        if kwargs.get("v_min") is not None or kwargs.get("v_max") is not None:
            out.domain = Domain(
                min=str(kwargs.get("v_min", "0")),
                max=str(kwargs.get("v_max", "1")),
            )
        _ = t_min, t_max
        return out

    def to_expression_fields(self) -> dict[str, Any]:
        """Fields to merge into a Desmos expression item (excluding latex/id/type)."""
        data: dict[str, Any] = {}
        if self.color:
            data["color"] = normalize_color(self.color) or self.color
        if self.color_latex:
            data["colorLatex"] = self.color_latex
        if self.line_style:
            data["lineStyle"] = normalize_line_style(self.line_style)
        if self.line_width is not None:
            data["lineWidth"] = str(self.line_width)
        if self.line_opacity is not None:
            data["lineOpacity"] = str(self.line_opacity)
        if self.point_style:
            data["pointStyle"] = normalize_point_style(self.point_style)
        if self.point_size is not None:
            data["pointSize"] = str(self.point_size)
        if self.point_opacity is not None:
            data["pointOpacity"] = str(self.point_opacity)
        if self.fill is not None:
            data["fill"] = bool(self.fill)
        if self.fill_opacity is not None:
            data["fillOpacity"] = str(self.fill_opacity)
        if self.points is not None:
            data["points"] = bool(self.points)
        if self.lines is not None:
            data["lines"] = bool(self.lines)
        if self.hidden is not None:
            data["hidden"] = bool(self.hidden)
        if self.secret is not None:
            data["secret"] = bool(self.secret)
        if self.label is not None:
            data["label"] = self.label
        if self.show_label is not None:
            data["showLabel"] = bool(self.show_label)
        if self.label_size is not None:
            data["labelSize"] = self.label_size
        if self.label_orientation is not None:
            data["labelOrientation"] = self.label_orientation
        if self.drag_mode:
            data["dragMode"] = normalize_drag_mode(self.drag_mode)
        if self.parametric_domain is not None:
            data["parametricDomain"] = self.parametric_domain.to_dict()
        if self.polar_domain is not None:
            data["polarDomain"] = self.polar_domain.to_dict()
        if self.domain is not None:
            data["domain"] = self.domain.to_dict()
        if self.slider is not None:
            data["slider"] = self.slider.to_dict()
        if self.clickable is not None:
            data["clickableInfo"] = self.clickable.to_dict()
        if self.folder_id is not None:
            data["folderId"] = self.folder_id
        return data


def _as_domain(value: Any) -> Domain:
    if isinstance(value, Domain):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return Domain(min=str(value[0]), max=str(value[1]))
    if isinstance(value, dict) and "min" in value and "max" in value:
        return Domain(min=str(value["min"]), max=str(value["max"]))
    raise UnsupportedPythonError(f"domain must be (min, max), got {value!r}")
