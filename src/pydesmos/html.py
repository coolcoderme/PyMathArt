"""Render a Desmos graph state as a standalone HTML page."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

# Public demo API key used in Desmos' own API documentation examples.
# For production sites, request a key at https://www.desmos.com/my-api
DEFAULT_API_KEY = "dcb31709b452b1cf9dc26972add0fda6"
DEFAULT_API_VERSION = "1.13"

Target = Literal["2d", "3d"]


def render_html(
    state: dict[str, Any],
    *,
    target: Target = "2d",
    title: str = "pydesmos graph",
    api_key: Optional[str] = None,
    api_version: str = DEFAULT_API_VERSION,
    width: str = "100%",
    height: str = "100vh",
    calculator_options: Optional[dict[str, Any]] = None,
) -> str:
    """Return a complete HTML page that loads ``state`` via ``setState``."""
    key = api_key or DEFAULT_API_KEY
    options: dict[str, Any] = {
        "expressions": True,
        "settingsMenu": True,
        "zoomButtons": True,
        "actions": True,
        "tone": True,
        "lockViewport": False,
    }
    if calculator_options:
        options.update(calculator_options)
    if target == "3d":
        ctor = "Desmos.Calculator3D"
    else:
        ctor = "Desmos.GraphingCalculator"
    # Graphs that use tone() start muted; expose a small unmute hint.
    has_tone = _state_uses_tone(state)
    state_json = json.dumps(state, ensure_ascii=False)
    options_json = json.dumps(options, ensure_ascii=False)
    script_src = (
        f"https://www.desmos.com/api/v{api_version}/calculator.js?apiKey={key}"
    )
    hint = ""
    if has_tone:
        hint = (
            '<p class="hint">This graph uses <code>tone()</code>. '
            "Desmos starts muted — click Unmute All or press Alt+M.</p>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{_escape(title)}</title>
  <script src="{script_src}"></script>
  <style>
    html, body {{ margin: 0; padding: 0; height: 100%; font-family: system-ui, sans-serif; }}
    #calculator {{ width: {width}; height: {height}; }}
    .hint {{ margin: 0; padding: 8px 12px; background: #111; color: #eee; font-size: 14px; }}
    code {{ font-family: ui-monospace, monospace; }}
  </style>
</head>
<body>
  {hint}
  <div id="calculator"></div>
  <script>
    (function () {{
      var elt = document.getElementById("calculator");
      var options = {options_json};
      var calculator = {ctor}(elt, options);
      var state = {state_json};
      calculator.setState(state);
      window.calculator = calculator;
    }})();
  </script>
</body>
</html>
"""


def _state_uses_tone(state: dict[str, Any]) -> bool:
    items = state.get("expressions", {}).get("list", [])
    for item in items:
        latex = item.get("latex") or ""
        if "tone" in latex:
            return True
    return False


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
