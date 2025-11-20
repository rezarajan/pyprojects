"""
Minimal Jinja2-based renderer. Loads base template from package templates.
"""

from __future__ import annotations

from jinja2 import Environment, PackageLoader, select_autoescape
from resume_generator.core.model import Resume


def get_jinja_env() -> Environment:
    return Environment(
        loader=PackageLoader("resume_generator", "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_html(resume: Resume, template_name: str = "harvard") -> str:
    env = get_jinja_env()
    template = env.get_template(f"{template_name}/base.html.j2")
    return template.render(resume=resume)
