from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from premailer import transform

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html"]),
)


def render_email(template_name: str, context: dict) -> str:
    html = _env.get_template(template_name).render(**context)
    return transform(html)
