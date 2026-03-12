import contextlib
import io
import json

from app.services.exceptions import InvalidParamsJsonError, TaskExecutionError


def run_python_task(python_code: str | None, params_json: str | None) -> dict[str, str | None]:
    """Execute trusted internal python code in a minimally restricted context."""

    if not python_code or not python_code.strip():
        raise TaskExecutionError("python_code is empty")

    try:
        params = json.loads(params_json) if params_json else {}
    except json.JSONDecodeError as exc:
        raise InvalidParamsJsonError("Invalid params_json") from exc

    safe_builtins = {
        "print": print,
        "len": len,
        "sum": sum,
        "min": min,
        "max": max,
        "range": range,
        "enumerate": enumerate,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
    }

    locals_ctx: dict[str, object] = {"params": params, "result": None}
    output_buffer = io.StringIO()

    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(python_code, {"__builtins__": safe_builtins}, locals_ctx)
    except Exception as exc:
        raise TaskExecutionError(f"Python execution failed: {exc}") from exc

    result_obj = locals_ctx.get("result")
    printed_text = output_buffer.getvalue().strip()

    if isinstance(result_obj, dict):
        summary = str(result_obj.get("summary", "Python task executed"))
        artifact_type = str(result_obj.get("artifact_type", "text"))
        return {
            "summary": summary,
            "artifact_type": artifact_type,
            "content_text": result_obj.get("content_text") or printed_text,
            "content_json": json.dumps(result_obj, ensure_ascii=False),
            "content_html": result_obj.get("content_html"),
        }

    return {
        "summary": "Python task executed",
        "artifact_type": "text",
        "content_text": printed_text or "Python code executed successfully",
        "content_json": json.dumps({"params": params}, ensure_ascii=False),
        "content_html": None,
    }
