"""Command-line interface: ``python -m pydesmos FILE.py``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydesmos.transpile import transpile_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pydesmos",
        description="Transpile Python into a Desmos graph-state JSON (and optional HTML).",
    )
    parser.add_argument("source", type=Path, help="Python file written in the pydesmos DSL")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Write graph-state JSON here (default: <source>.json)",
    )
    parser.add_argument(
        "--html",
        type=Path,
        nargs="?",
        const=True,
        default=None,
        help="Also write an HTML page that loads the state with the Desmos API",
    )
    parser.add_argument(
        "--target",
        choices=("2d", "3d", "auto"),
        default="auto",
        help="Desmos calculator: graphing (2d), 3D, or auto-detect from helpers",
    )
    parser.add_argument("--title", default=None, help="HTML page title")
    parser.add_argument(
        "--xmin", type=float, default=None, help="Viewport xmin (and similarly xmax/ymin/ymax/zmin/zmax)"
    )
    parser.add_argument("--xmax", type=float, default=None)
    parser.add_argument("--ymin", type=float, default=None)
    parser.add_argument("--ymax", type=float, default=None)
    parser.add_argument("--zmin", type=float, default=None)
    parser.add_argument("--zmax", type=float, default=None)
    args = parser.parse_args(argv)

    if not args.source.exists():
        parser.error(f"file not found: {args.source}")

    graph = transpile_file(
        args.source,
        target=None if args.target == "auto" else args.target,
        title=args.title,
        xmin=args.xmin,
        xmax=args.xmax,
        ymin=args.ymin,
        ymax=args.ymax,
        zmin=args.zmin,
        zmax=args.zmax,
    )
    out = args.out or args.source.with_suffix(".json")
    graph.save(out)
    html_path = args.html
    if html_path is True:
        html_path = out.with_suffix(".html")
    if html_path:
        graph.save_html(html_path, title=args.title or graph.title)
        print(f"wrote {out} and {html_path}")
    else:
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
