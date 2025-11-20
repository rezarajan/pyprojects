# Minimal CLI using argparse that loads a TOML and writes HTML output via renderer.
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from resume_generator.core.loader import load_toml
from resume_generator.core.model import Resume
from resume_generator.render.html_renderer import render_html


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="resume-gen", description="Generate Harvard-style resume from TOML"
    )
    p.add_argument("input", type=Path, help="Input TOML file")
    p.add_argument(
        "--html", type=Path, default=Path("out.html"), help="Output HTML file"
    )
    p.add_argument("--pdf", type=Path, help="Output PDF file (optional)")
    p.add_argument(
        "--template",
        type=str,
        default="harvard",
        help="Template name (default: harvard)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data = load_toml(args.input)
    except Exception as e:
        print(f"Error loading TOML: {e}")
        return 2

    resume = Resume.from_dict(data)

    html = render_html(resume, template_name=args.template)

    args.html.write_text(html, encoding="utf-8")
    print(f"Wrote HTML to {args.html}")

    # PDF generation will be added in later step
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
