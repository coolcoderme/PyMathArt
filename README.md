# pydesmos

Transpile **Python** into **Desmos** graphing-calculator formulas and a graph state that `Calc.setState()` (or the 3D calculator) can load.

Write variables, functions, lists, piecewise conditionals, sliders, shapes, clickable actions, and `tone()` in Python. pydesmos walks the AST, emits Desmos LaTeX, and packages it as importable JSON — plus an optional HTML page that boots the official Desmos API.

```python
from pydesmos import transpile

graph = transpile("""
a = slider(2, min=0, max=5)
def f(x):
    return a * x ** 2
point(1, f(1), label="P")
""")

graph.save("parabola.json")
graph.save_html("parabola.html")
```

Open the JSON in any page that calls `calculator.setState(...)`, or just open the HTML file.

## Install

```bash
pip install -e .
# or, for tests:
pip install -e ".[dev]"
```

Python 3.9+. No runtime dependencies.

```bash
python -m pydesmos examples/rose_curve.py --html
python -m pydesmos examples/surface_3d.py --target 3d --html
```

## What maps to Desmos

| Python | Desmos |
| --- | --- |
| `a = 2` | `a=2` |
| `a = slider(1, 0, 10)` | Slider with those bounds |
| `def f(x): return x**2` | `f\left(x\right)=x^{2}` |
| `f = lambda x: x**2` | same |
| `if / elif / else` in a function | Piecewise `\left\{cond:val,\ldots\right\}` |
| `x if c else y` | Piecewise |
| `[i**2 for i in range(1, 11)]` | List comprehension over `[1...10]` |
| `xs = []; for i in range(n): xs.append(...)` | Same list comprehension |
| `sum(i**2 for i in range(1, n+1))` | `\sum_{i=1}^{n}i^{2}` |
| `n += 1` | Action `n\to n+1` |
| `action(score=score+1)` | Named or bare action (`\to`) |
| `point(..., on_click=...)` | `clickableInfo` on that object |
| `ticker(action, interval_ms=16)` | Graph ticker (`dt` is elapsed ms) |
| `tone(440, 0.5)` | Desmos `tone()` |
| `polygon`, `segment`, `circle` | Geometry helpers |
| `parametric(...)`, `polar(...)` | Curves with domain bounds |
| `x**2 + y**2 < 1` | Inequality / filled region |
| `surface`, `sphere`, `point3d` | 3D calculator (auto-selected) |

Module docstrings and `note("...")` become expression-list notes. `folder("title")` groups following items until `end_folder()`.

### Identifiers

Desmos multiplies adjacent letters (`xy` means `x*y`), so Python names longer than one character become a first letter plus a subscript: `score` → `s_{core}`. Greek names (`theta`, `pi`, `alpha`, …) and specials (`dt`, `index`) stay whole tokens. Trailing digits become subscripts: `a1` → `a_{1}`.

Lists in Desmos are **1-indexed**. Python `range` is exclusive-end and is converted to inclusive Desmos lists (`range(1, 11)` → `[1...10]`).

`log(x)` follows **Python** (natural log → `\ln`). Use `log10(x)` or `log(x, b)` for other bases.

## API

### `transpile(source, target=None, **viewport) -> Graph`

`source` may be a Python string, a `.py` path, a parsed AST, or a function (its body is transpiled).

`target` is `"2d"` (graphing calculator) or `"3d"`. If omitted, 3D helpers (`surface`, `sphere`, `point3d`, 3-component `parametric`) select 3D.

### `Graph`

Builder returned by `transpile`, also usable by hand:

```python
from pydesmos import Graph

g = Graph(target="2d")
g.note("A line")
g.slider("m", 1, -5, 5)
g.expression(r"y=m\cdot x")
state = g.to_state()       # dict for setState
g.to_json()
g.to_html()
g.save("line.json")
g.save_html("line.html")
```

The state envelope matches live Desmos graphs (currently `version: 11`): `graph.viewport`, `expressions.list[]` with `type` / `id` / `latex`, optional `clickableInfo`, `slider`, domains, and `expressions.ticker`.

### Helpers recognized in the DSL

`slider`, `point`, `point3d`, `segment`, `polygon`, `circle`, `parametric`, `polar`, `inequality`, `tone`, `ticker`, `action`, `assign`, `note`, `folder`, `end_folder`, `raw` / `latex` (passthrough), `surface`, `triangle`, `sphere`, `viewport`, `graph_settings`, `rgb`, `hsv`.

Style kwargs: `color` (name or `#rrggbb`), `line_style` (`SOLID`/`DASHED`/`DOTTED`), `line_width`, `line_opacity` / `opacity`, `point_style`, `point_size`, `fill`, `fill_opacity`, `label`, `drag_mode`, `hidden`, `on_click`, `t_min` / `t_max`, `u_min` / `u_max`, `v_min` / `v_max`.

### HTML export

Pages load `https://www.desmos.com/api/v1.13/calculator.js` with Desmos’ public demo API key (the same one used in their docs). For a deployed site, get your own key at [desmos.com/my-api](https://www.desmos.com/my-api) and pass `api_key=...` to `to_html()`. 2D uses `Desmos.GraphingCalculator`; 3D uses `Desmos.Calculator3D`. Graphs that contain `tone()` remind you that Desmos starts **muted** (Unmute All / Alt+M).

## Examples

| File | What it shows |
| --- | --- |
| `examples/rose_curve.py` | Polar rose, sliders, dotted circle |
| `examples/lissajous_art.py` | Parametric Lissajous + filled polygon |
| `examples/clickable_game.py` | Actions, clickable target/reset, ticker |
| `examples/tone_demo.py` | `tone()`, clickable keys, optional sweep ticker |
| `examples/surface_3d.py` | 3D surface, sphere, helix, parametric band |

```bash
python -m pydesmos examples/clickable_game.py --html
```

## Unsupported Python

Constructs that do not map to Desmos fail with `UnsupportedPythonError` (line + column):

- classes, `async`, `try`/`except`, `with`, `while`, `yield`, walrus `:=`, f-strings
- imports other than `math` / `pydesmos`
- module-level `if` (except `if __name__ == "__main__"`, which is skipped)
- for-loops that are not “start with `xs = []`, then `xs.append(expr)`”
- function bodies that are not a return, piecewise returns, or leading locals + `with`

Desmos also cannot express general Python mutation, I/O, or third-party libraries.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

CI runs pytest on Python 3.9 / 3.11 / 3.12 and transpiles every example into valid graph-state JSON.

## Limitations

- Output is the documented `setState` JSON envelope plus Desmos LaTeX. Desmos itself still decides whether a formula plots; this library checks braces / `\left`–`\right` pairing, not the full Desmos parser.
- 3D viewport extras (`worldRotation3D`, `zmin`/`zmax`) follow saved 3D graphs. Exact camera fields can vary by calculator version; expressions still load if you `setState` on `Desmos.Calculator3D`.
- `tone()` is continuous while unmuted; “triggering” a note is done by driving frequency/gain from an action or ticker, which is how Desmos works.
- Clickable objects need Actions enabled (the HTML page passes `actions: true`).
- Recursion is emitted as written; Desmos recursive functions have their own restrictions.
- Graph-state `version` is `11` (current on desmos.com). Older API embeds may migrate it on load.

## License

MIT. See [LICENSE](LICENSE).
