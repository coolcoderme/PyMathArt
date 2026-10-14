from __future__ import annotations

from pydesmos import transpile
from pydesmos.validate import validate_state


def exprs(src: str, **kwargs):
    state = transpile(src, **kwargs).to_state()
    validate_state(state)
    return [i for i in state["expressions"]["list"] if i["type"] == "expression"], state


def test_point_segment_polygon_circle():
    src = """
point(1, 2, color="red", label="A", drag_mode="XY")
segment((0, 0), (1, 1), color="blue", line_style="DASHED")
polygon((0, 0), (1, 0), (0, 1), fill=True, fill_opacity=0.3, color="green")
circle((0, 0), 2, fill=True, color="purple")
"""
    items, _ = exprs(src)
    assert items[0]["latex"] == r"\left(1,2\right)"
    assert items[0]["color"] == "#c74440"
    assert items[0]["label"] == "A"
    assert items[0]["showLabel"] is True
    assert items[0]["dragMode"] == "XY"
    assert "polygon" in items[1]["latex"]
    assert items[1]["lineStyle"] == "DASHED"
    assert items[1]["fill"] is False
    assert items[2]["fill"] is True
    assert items[2]["fillOpacity"] == "0.3"
    assert r"x^{2}+y^{2}\le{}" in items[3]["latex"]


def test_parametric_and_polar():
    src = """
parametric(cos(t), sin(t), t_min=0, t_max=2 * pi, color="#000000", line_width=4)
polar(cos(2 * t), t_min=0, t_max=2 * pi, color="orange")
"""
    items, _ = exprs(src)
    assert items[0]["latex"].startswith(r"\left(")
    assert items[0]["parametricDomain"]["min"] == "0"
    assert r"\pi" in items[0]["parametricDomain"]["max"]
    assert items[0]["lineWidth"] == "4"
    assert items[1]["latex"].startswith("r=")
    assert r"\theta" in items[1]["latex"]
    assert "polarDomain" in items[1]
    assert "parametricDomain" not in items[1]


def test_named_point_assignment():
    items, _ = exprs("P = point(3, 4, color='black')")
    assert items[0]["latex"] == r"P=\left(3,4\right)"


def test_rgb_color_latex():
    items, _ = exprs("point(0, 0, color_latex=rgb(255, 0, 0))")
    assert "colorLatex" in items[0]
    assert "rgb" in items[0]["colorLatex"]


def test_sphere_and_surface_3d():
    src = """
surface(x ** 2 + y ** 2, color="blue")
sphere((0, 0, 0), 2, color="red")
point3d(1, 1, 1, label="p")
"""
    items, state = exprs(src)
    assert items[0]["latex"].startswith("z=")
    assert "z^{2}" in items[1]["latex"] or "z-" in items[1]["latex"]
    assert items[2]["latex"] == r"\left(1,1,1\right)"
    assert "zmin" in state["graph"]["viewport"]


def test_inequality_fill():
    items, _ = exprs("x ** 2 + y ** 2 <= 4")
    assert r"x^{2}+y^{2}\le{}4" == items[0]["latex"]
