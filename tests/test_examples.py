from __future__ import annotations

import json
from pathlib import Path

import pytest

from pydesmos import transpile_file, validate_state
from pydesmos.validate import latex_strings

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

CASES = [
    ("rose_curve.py", "2d", ["r=", r"\theta"]),
    ("lissajous_art.py", "2d", [r"\operatorname{polygon}", r"\sin"]),
    ("clickable_game.py", "2d", [r"\to", "ticker"]),
    ("tone_demo.py", "2d", [r"\operatorname{tone}", r"\to"]),
    ("surface_3d.py", "3d", ["z=", r"\left("]),
]


@pytest.mark.parametrize("filename,target,needles", CASES)
def test_example_state(filename, target, needles):
    path = EXAMPLES / filename
    graph = transpile_file(path, target=target)
    state = graph.to_state()
    validate_state(state)
    assert state["version"] == 11
    assert state["graph"]["viewport"]["xmin"] < state["graph"]["viewport"]["xmax"]
    blob = json.dumps(state)
    json.loads(blob)
    joined = "\n".join(latex_strings(state))
    for needle in needles:
        if needle == "ticker":
            assert "ticker" in state["expressions"]
        else:
            assert needle in joined, f"{filename} missing {needle!r} in {joined}"
    if target == "3d":
        assert "zmin" in state["graph"]["viewport"]
        html = graph.to_html()
        assert "Calculator3D" in html
    else:
        html = graph.to_html()
        assert "GraphingCalculator" in html
    # Every example should produce at least one plottable expression.
    exprs = [i for i in state["expressions"]["list"] if i["type"] == "expression"]
    assert exprs, filename


def test_clickable_example_has_clickable_info():
    state = transpile_file(EXAMPLES / "clickable_game.py").to_state()
    clickables = [
        i for i in state["expressions"]["list"] if i.get("clickableInfo", {}).get("enabled")
    ]
    assert len(clickables) >= 2
    assert state["expressions"]["ticker"]["handlerLatex"]


def test_tone_example_has_tone_and_keys():
    state = transpile_file(EXAMPLES / "tone_demo.py").to_state()
    latex = "\n".join(latex_strings(state))
    assert r"\operatorname{tone}" in latex
    polys = [i for i in state["expressions"]["list"] if "polygon" in (i.get("latex") or "")]
    assert len(polys) >= 3
    assert all(p.get("clickableInfo") for p in polys)


def test_rose_has_slider_and_polar_domain():
    state = transpile_file(EXAMPLES / "rose_curve.py").to_state()
    sliders = [i for i in state["expressions"]["list"] if "slider" in i]
    assert len(sliders) >= 2
    polar = next(i for i in state["expressions"]["list"] if (i.get("latex") or "").startswith("r="))
    assert "polarDomain" in polar
