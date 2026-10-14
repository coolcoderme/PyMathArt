"""Polar rose — math art with sliders for amplitude and petal count."""
from pydesmos import circle, cos, note, pi, polar, slider, t, viewport

viewport(xmin=-6, xmax=6, ymin=-6, ymax=6)
note("r = a cos(n θ). Odd n → n petals, even n → 2n petals.")

a = slider(2.5, min=0.5, max=5, step=0.1)
n = slider(5, min=1, max=12, step=1)

polar(a * cos(n * t), t_min=0, t_max=2 * pi, color="#c74440", line_width=3)
circle((0, 0), a, color="#2d70b3", line_style="DOTTED", hidden=False)
