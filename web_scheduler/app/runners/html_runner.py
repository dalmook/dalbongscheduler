import json

from jinja2 import Template

from app.services.exceptions import InvalidParamsJsonError, TaskExecutionError


def run_html_task(html_template: str | None, params_json: str | None) -> dict[str, str | None]:
    if not html_template or not html_template.strip():
        raise TaskExecutionError("html_template is empty")

    try:
        params = json.loads(params_json) if params_json else {}
    except json.JSONDecodeError as exc:
        raise InvalidParamsJsonError("Invalid params_json") from exc

    try:
        rendered = Template(html_template).render(**params)
    except Exception as exc:
        raise TaskExecutionError(f"HTML render failed: {exc}") from exc

    return {
        "summary": "HTML template rendered",
        "artifact_type": "html",
        "content_text": None,
        "content_json": json.dumps(params, ensure_ascii=False),
        "content_html": rendered,
    }
