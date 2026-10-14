from __future__ import annotations

from pydesmos import transpile
from pydesmos.validate import latex_strings, validate_state


def latex_list(src: str, **kwargs):
    g = transpile(src, **kwargs)
    state = g.to_state()
    return [item["latex"] for item in state["expressions"]["list"] if "latex" in item], state


def test_assignments_and_function():
    src = """
a = 2
def f(x):
    return a * x ** 2
"""
    latex, state = latex_list(src)
    validate_state(state)
    assert latex[0] == "a=2"
    assert latex[1].startswith(r"f\left(x\right)=")
    assert "x^{2}" in latex[1]


def test_lambda_function():
    latex, _ = latex_list("f = lambda x, y: x + y")
    assert latex[0] == r"f\left(x,y\right)=x+y"


def test_piecewise_function():
    src = """
def abs_val(x):
    if x >= 0:
        return x
    else:
        return -x
"""
    latex, _ = latex_list(src)
    assert latex[0] == r"a_{bs_val}\left(x\right)=\left\{x\ge{}0:x,-x\right\}"


def test_piecewise_elif():
    src = """
def f(x):
    if x < 0:
        return -1
    elif x == 0:
        return 0
    else:
        return 1
"""
    latex, _ = latex_list(src)
    assert r"x<0:-1" in latex[0]
    assert r"x=0:0" in latex[0]


def test_function_with_substitution():
    src = """
def f(x):
    a = x + 1
    return a ** 2
"""
    latex, _ = latex_list(src)
    assert r"\operatorname{with}" in latex[0]
    assert "a=x+1" in latex[0]


def test_list_comprehension_and_loop():
    src = """
xs = [i ** 2 for i in range(1, 6)]
ys = []
for i in range(4):
    ys.append(i + 1)
"""
    latex, _ = latex_list(src)
    assert latex[0] == r"x_{s}=\left[i^{2}\operatorname{for}i=\left[1...5\right]\right]"
    assert "y_{s}=" in latex[1]
    assert r"\operatorname{for}" in latex[1]


def test_slider_and_note():
    src = """
note("hello")
a = slider(1, min=0, max=10, step=0.5)
"""
    g = transpile(src)
    state = g.to_state()
    notes = [i for i in state["expressions"]["list"] if i["type"] == "text"]
    sliders = [i for i in state["expressions"]["list"] if i.get("type") == "expression" and "slider" in i]
    assert notes[0]["text"] == "hello"
    assert sliders[0]["latex"] == "a=1"
    assert sliders[0]["slider"]["min"] == "0"
    assert sliders[0]["slider"]["max"] == "10"
    assert sliders[0]["slider"]["step"] == "0.5"


def test_module_docstring_becomes_note():
    src = '''"""A graph."""
y = x ** 2
'''
    g = transpile(src)
    state = g.to_state()
    assert state["expressions"]["list"][0]["type"] == "text"
    assert "A graph" in state["expressions"]["list"][0]["text"]


def test_skip_if_main():
    src = """
a = 1
if __name__ == "__main__":
    print(a)
"""
    latex, _ = latex_list(src)
    assert latex == ["a=1"]


def test_skip_pydesmos_imports():
    src = """
from pydesmos import slider, note
import math
a = slider(3, 0, 5)
"""
    latex, _ = latex_list(src)
    assert latex == ["a=3"]


def test_inequality_statement():
    latex, _ = latex_list("x ** 2 + y ** 2 < 1")
    assert latex[0] == r"x^{2}+y^{2}<1"


def test_raw_latex():
    latex, _ = latex_list(r'raw(r"y=\sin(x)")')
    assert latex[0] == r"y=\sin(x)"


def test_callable_source():
    def scene():
        k = 3
        y = k * x  # noqa: F821

    g = transpile(scene)
    state = g.to_state()
    latex = [i["latex"] for i in state["expressions"]["list"] if "latex" in i]
    assert latex[0] == "k=3"
    assert "y=" in latex[1]


def test_target_2d_viewport_defaults():
    g = transpile("a = 1", target="2d")
    vp = g.to_state()["graph"]["viewport"]
    assert vp["xmin"] == -10
    assert "zmin" not in vp


def test_target_3d_auto_from_surface():
    g = transpile("surface(x ** 2 + y ** 2)")
    assert g.target == "3d"
    state = g.to_state()
    assert "zmin" in state["graph"]["viewport"]
    assert any("z=" in (i.get("latex") or "") for i in state["expressions"]["list"])


def test_explicit_2d_overrides_3d_helper():
    g = transpile("surface(x ** 2 + y ** 2)", target="2d")
    assert g.target == "2d"


def test_folder_groups_expressions():
    src = """
folder("Art")
a = 1
end_folder()
b = 2
"""
    g = transpile(src)
    items = g.to_state()["expressions"]["list"]
    folder = next(i for i in items if i["type"] == "folder")
    a = next(i for i in items if i.get("latex") == "a=1")
    b = next(i for i in items if i.get("latex") == "b=2")
    assert a["folderId"] == folder["id"]
    assert "folderId" not in b


def test_version_and_ids():
    state = transpile("a = 1\nb = 2").to_state()
    assert state["version"] == 11
    ids = [i["id"] for i in state["expressions"]["list"]]
    assert ids == ["1", "2"]
    assert list(latex_strings(state)) == ["a=1", "b=2"]
