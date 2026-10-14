from __future__ import annotations

from pydesmos import transpile
from pydesmos.validate import validate_state


def state_of(src: str):
    g = transpile(src)
    s = g.to_state()
    validate_state(s)
    return s


def test_augmented_assignment_is_action():
    s = state_of("n = 0\nn += 1")
    latex = [i["latex"] for i in s["expressions"]["list"] if "latex" in i]
    assert latex[0] == "n=0"
    assert latex[1] == r"n\to{n+1}"


def test_named_and_multi_action():
    src = """
score = 0
lives = 3
hit = action(score=score + 1)
reset = action(score=0, lives=3)
"""
    s = state_of(src)
    latex = [i["latex"] for i in s["expressions"]["list"] if "latex" in i]
    assert any(r"s_{core}\to{" in x and r"s_{core}+1" in x for x in latex)
    assert any(r"\to" in x and r"l_{ives}" in x for x in latex)


def test_clickable_point():
    src = """
n = 0
point(0, 0, on_click=action(n=n + 1), click_description="bump")
"""
    s = state_of(src)
    pt = next(i for i in s["expressions"]["list"] if i.get("latex") == r"\left(0,0\right)")
    info = pt["clickableInfo"]
    assert info["enabled"] is True
    assert r"n\to{n+1}" in info["latex"]
    assert info["description"] == "bump"


def test_clickable_from_string_arrow():
    src = 'point(1, 1, on_click="n -> n+1")'
    s = state_of(src)
    pt = s["expressions"]["list"][-1]
    assert r"\to" in pt["clickableInfo"]["latex"]


def test_ticker():
    src = """
tval = 0
ticker(assign("tval", tval + dt), interval_ms=16, playing=True)
"""
    s = state_of(src)
    ticker = s["expressions"]["ticker"]
    assert ticker["playing"] is True
    assert ticker["minStepLatex"] == "16"
    assert r"\to" in ticker["handlerLatex"]
    assert r"\operatorname{dt}" in ticker["handlerLatex"]


def test_tone_expression():
    src = """
freq = slider(440, min=110, max=880)
gain = slider(0.5, min=0, max=1)
tone(freq, gain)
"""
    s = state_of(src)
    latex = [i["latex"] for i in s["expressions"]["list"] if "latex" in i]
    assert any(r"\operatorname{tone}" in x for x in latex)


def test_standalone_action():
    s = state_of("action(n, n + 1)")
    assert s["expressions"]["list"][0]["latex"] == r"n\to{n+1}"
