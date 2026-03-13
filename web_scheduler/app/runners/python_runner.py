import contextlib
import io
import json

from app.services.exceptions import InvalidParamsJsonError, TaskExecutionError


def run_python_task(python_code: str | None, params_json: str | None) -> dict[str, str | None]:
    """Execute trusted internal python code with full builtins/modules.

    Note: this is intentionally permissive for internal trusted usage.
    """

    if not python_code or not python_code.strip():
        raise TaskExecutionError("python_code is empty")

    try:
        params = json.loads(params_json) if params_json else {}
    except json.JSONDecodeError as exc:
        raise InvalidParamsJsonError("Invalid params_json") from exc

    locals_ctx: dict[str, object] = {
        "params": params,
        "result": None,
    }
    output_buffer = io.StringIO()

    globals_ctx = {
        "__builtins__": __builtins__,
    }

    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(python_code, globals_ctx, locals_ctx)
    except Exception as exc:
        raise TaskExecutionError(f"Python execution failed: {exc}") from exc

    result_obj = locals_ctx.get("result")
    printed_text = output_buffer.getvalue().strip()

    html_candidate = None
    for key in ("result_html", "RESULT_HTML", "__RESULT_HTML__", "html"):
        val = locals_ctx.get(key)
        if isinstance(val, str) and val.strip():
            html_candidate = val
            break

    # fallback: stdout로 HTML을 print한 경우도 HTML 결과로 인식
    if not html_candidate and printed_text:
        t = printed_text.lower()
        if any(tag in t for tag in ("<html", "<table", "<div", "<body", "</")):
            html_candidate = printed_text

    if isinstance(result_obj, dict):
        summary = str(result_obj.get("summary", "Python task executed"))
        artifact_type = str(result_obj.get("artifact_type", "text"))
        content_html = result_obj.get("content_html") or html_candidate
        if content_html and artifact_type == "text":
            artifact_type = "html"
        return {
            "summary": summary,
            "artifact_type": artifact_type,
            "content_text": result_obj.get("content_text") or printed_text,
            "content_json": json.dumps(result_obj, ensure_ascii=False),
            "content_html": content_html,
        }

    if html_candidate:
        return {
            "summary": "Python task executed",
            "artifact_type": "html",
            "content_text": printed_text or "",
            "content_json": json.dumps({"params": params}, ensure_ascii=False),
            "content_html": html_candidate,
        }

    return {
        "summary": "Python task executed",
        "artifact_type": "text",
        "content_text": printed_text or "Python code executed successfully",
        "content_json": json.dumps({"params": params}, ensure_ascii=False),
        "content_html": None,
    }
