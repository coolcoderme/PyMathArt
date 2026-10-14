"""3D hyperbolic paraboloid, a sphere, and a space curve."""
from pydesmos import (
    cos,
    note,
    parametric,
    pi,
    point3d,
    sin,
    slider,
    sphere,
    surface,
    t,
    u,
    v,
    viewport,
)

viewport(xmin=-5, xmax=5, ymin=-5, ymax=5, zmin=-5, zmax=5)
note("z = a(x² − y²). Drag a, and inspect the sphere and helix.")

a = slider(0.35, min=0.05, max=1, step=0.05)

surface(a * (x**2 - y**2), color="#2d70b3", fill_opacity=0.55)
sphere((0, 0, 0), 1.2, color="#c74440", line_style="DOTTED")
point3d(0, 0, 0, color="#000000", label="origin", point_size=12)

parametric(
    2 * cos(t),
    2 * sin(t),
    0.4 * t,
    t_min=-pi,
    t_max=pi,
    color="#fa7e19",
    line_width=3,
)

# Parametric torus-like band (u, v).
parametric(
    (2.8 + 0.45 * cos(v)) * cos(u),
    (2.8 + 0.45 * cos(v)) * sin(u),
    0.45 * sin(v),
    u_min=0,
    u_max=2 * pi,
    v_min=0,
    v_max=2 * pi,
    color="#6042a6",
    fill_opacity=0.4,
)
