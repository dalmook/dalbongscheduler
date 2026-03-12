import csv
import io
import json

from app.services.exceptions import TaskExecutionError


def run_sql_task(sql_code: str | None, output_format: str | None = None) -> dict[str, str | None]:
    """Mock SQL runner for flow validation. No external DB connection in phase 2."""

    if not sql_code or not sql_code.strip():
        raise TaskExecutionError("sql_code is empty")

    rows = [
        {"row_no": 1, "metric": "alpha", "value": 10},
        {"row_no": 2, "metric": "beta", "value": 20},
        {"row_no": 3, "metric": "gamma", "value": 30},
    ]

    fmt = (output_format or "json").lower()
    summary = f"SQL task executed in mock mode (rows={len(rows)})"

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        content = output.getvalue()
        return {
            "summary": summary,
            "artifact_type": "csv",
            "content_text": content,
            "content_json": json.dumps({"sql": sql_code, "rows": rows}, ensure_ascii=False),
            "content_html": None,
        }

    if fmt == "text":
        text_content = "\n".join(f"{row['row_no']}: {row['metric']}={row['value']}" for row in rows)
        return {
            "summary": summary,
            "artifact_type": "text",
            "content_text": text_content,
            "content_json": json.dumps({"sql": sql_code, "rows": rows}, ensure_ascii=False),
            "content_html": None,
        }

    return {
        "summary": summary,
        "artifact_type": "json",
        "content_text": None,
        "content_json": json.dumps({"sql": sql_code, "rows": rows}, ensure_ascii=False, indent=2),
        "content_html": None,
    }
