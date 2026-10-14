from __future__ import annotations

import json

import pytest

from pydesmos import Graph, GraphStateError, transpile, validate_state
from pydesmos.state import GRAPH_STATE_VERSION, build_state


def test_programmatic_graph():
    g = Graph(target="2d")
    g.note("hi")
    g.slider("a", 1, 0, 5)
    g.expression(r"y=a\cdot x")
    state = g.to_state()
    assert state["version"] == GRAPH_STATE_VERSION
    assert len(state["expressions"]["list"]) == 3
    json.dumps(state)  # serializable


def test_validate_rejects_bad_envelope():
    with pytest.raises(GraphStateError):
        validate_state({})
    with pytest.raises(GraphStateError):
        validate_state({"version": 11, "graph": {}, "expressions": {"list": []}})
    with pytest.raises(GraphStateError):
        validate_state(
            {
                "version": 11,
                "graph": {"viewport": {"xmin": 0, "xmax": 1, "ymin": 0, "ymax": 1}},
                "expressions": {
                    "list": [{"type": "expression", "id": "1", "latex": r"\left(1"}]
                },
            }
        )


def test_round_trip_json():
    state = transpile("a = 1\npoint(0, 0)").to_state()
    payload = json.loads(json.dumps(state))
    validate_state(payload)


def test_build_state_3d_has_rotation():
    state = build_state([], target="3d")
    validate_state(state)
    assert "worldRotation3D" in state["graph"]
    assert state["graph"]["viewport"]["zmin"] == -5


def test_html_contains_setstate_and_api():
    html = transpile("a = 1").to_html(title="unit")
    assert "setState" in html
    assert "Desmos.GraphingCalculator" in html
    assert "calculator.js" in html
    assert "unit" in html


def test_html_3d_uses_calculator3d():
    html = transpile("surface(x ** 2 + y ** 2)", target="3d").to_html()
    assert "Desmos.Calculator3D" in html


def test_html_mentions_unmute_when_tone_present():
    html = transpile("tone(440)").to_html()
    assert "Unmute" in html
    assert "tone" in html
