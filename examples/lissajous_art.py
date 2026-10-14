"""Lissajous curves and a stained-glass polygon — math art."""
from pydesmos import (
    cos,
    note,
    parametric,
    pi,
    polygon,
    sin,
    slider,
    t,
    viewport,
)

viewport(xmin=-4, xmax=4, ymin=-3, ymax=3)
note("Lissajous curve (a sin(n t), b sin(m t + δ)) plus a glass polygon.")

a = slider(2, min=0.5, max=3)
b = slider(1.5, min=0.5, max=3)
n = slider(3, min=1, max=8, step=1)
m = slider(4, min=1, max=8, step=1)
delta = slider(0.7, min=0, max=6.283)

parametric(
    a * sin(n * t),
    b * sin(m * t + delta),
    t_min=0,
    t_max=2 * pi,
    color="#6042a6",
    line_width=2.5,
)

polygon(
    (2.6, 1.6),
    (3.4, 0.4),
    (2.8, -1.2),
    (1.6, -1.6),
    (1.2, -0.2),
    fill=True,
    fill_opacity=0.35,
    color="#fa7e19",
    line_style="SOLID",
)
