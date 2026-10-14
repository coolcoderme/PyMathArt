"""Tones triggered by clickable keys and a ticker-driven frequency sweep."""
from pydesmos import (
    action,
    assign,
    note,
    point,
    polygon,
    slider,
    ticker,
    tone,
    viewport,
)

viewport(xmin=-2, xmax=10, ymin=-3, ymax=4)
note("Click a key to play that frequency. Unmute in Desmos (Alt+M). Gain is a slider.")

freq = 440
gain = slider(0.4, min=0, max=1, step=0.05)
playing = 1
sweep = 0

tone(freq, gain * playing)

play_a = action(freq=440, playing=1)
play_c = action(freq=523.25, playing=1)
play_e = action(freq=659.25, playing=1)
silence = action(playing=0)

# Piano-key polygons.
polygon(
    (0, 0),
    (2, 0),
    (2, 3),
    (0, 3),
    color="#c74440",
    fill=True,
    fill_opacity=0.7,
    label="A4 440",
    on_click=play_a,
    click_description="Play A4",
)
polygon(
    (2.3, 0),
    (4.3, 0),
    (4.3, 3),
    (2.3, 3),
    color="#2d70b3",
    fill=True,
    fill_opacity=0.7,
    label="C5",
    on_click=play_c,
    click_description="Play C5",
)
polygon(
    (4.6, 0),
    (6.6, 0),
    (6.6, 3),
    (4.6, 3),
    color="#388c46",
    fill=True,
    fill_opacity=0.7,
    label="E5",
    on_click=play_e,
    click_description="Play E5",
)

point(
    8,
    1.5,
    color="#000000",
    point_size=16,
    label="mute",
    on_click=silence,
    click_description="Silence",
)

# Optional siren: enable the ticker in Desmos to sweep frequency.
ticker(
    action(freq=220 + 220 * sweep, sweep=sweep + 0.02),
    interval_ms=50,
    playing=False,
)
