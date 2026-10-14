"""Clickable target practice — actions, clickable points, and a ticker."""
from pydesmos import (
    action,
    assign,
    note,
    pi,
    point,
    polygon,
    sin,
    slider,
    ticker,
    viewport,
)

viewport(xmin=-8, xmax=8, ymin=-6, ymax=6)
note("Click the red target. The ticker moves it; score and lives update on click.")

score = 0
lives = 3
omega = slider(1, min=0.2, max=3, step=0.1)
time = 0

# Named actions the clickable objects can fire.
hit = action(score=score + 1)
miss = action(lives=lives - 1)
reset = action(score=0, lives=3, time=0)

ticker(assign("time", time + 0.016), interval_ms=16, playing=False)

# Moving target. `index` is unused here; the action runs when the point is clicked.
target = point(
    4 * sin(omega * time),
    3 * sin(omega * time + pi / 2),
    color="#c74440",
    point_size=18,
    label="hit",
    on_click=hit,
    click_description="Score a hit",
)

# Reset button (a small square).
polygon(
    (-7.5, 5.2),
    (-5.5, 5.2),
    (-5.5, 4.2),
    (-7.5, 4.2),
    color="#2d70b3",
    fill=True,
    fill_opacity=0.5,
    label="reset",
    on_click=reset,
    click_description="Reset the game",
)

# Decorative "miss" zone — clicking the background polygon costs a life.
polygon(
    (-8, -6),
    (8, -6),
    (8, -5),
    (-8, -5),
    color="#000000",
    fill=True,
    fill_opacity=0.12,
    on_click=miss,
    click_description="Missed",
)
