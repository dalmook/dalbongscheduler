import csv
import io
import json
import re

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.services.exceptions import TaskExecutionError


def _is_write_query(sql: str) -> bool:
    head = re.sub(r"^\s+", "", sql).lower()
    write_prefixes = ("insert", "update", "delete", "merge", "drop", "alter", "create", "truncate", "grant", "revoke")
    return head.startswith(write_prefixes)


def _normalize_rows(result) -> list[dict]:
    keys = list(result.keys()) if hasattr(result, "keys") else []
    rows = []
    for row in result:
        rows.append({k: row[idx] for idx, k in enumerate(keys)})
    return rows


def run_sql_task(sql_code: str | None, output_format: str | None = None) -> dict[str, str | None]:
    """Execute SQL against real DB (SQL_RUNNER_DATABASE_URL), fallback to app DB URL.

    Safety defaults:
    - write queries blocked unless SQL_RUNNER_ALLOW_WRITE=true
    """

    if not sql_code or not sql_code.strip():
        raise TaskExecutionError("sql_code is empty")

    settings = get_settings()
    target_db_url = settings.sql_runner_database_url or settings.database_url

    if _is_write_query(sql_code) and not settings.sql_runner_allow_write:
        raise TaskExecutionError("write query blocked (set SQL_RUNNER_ALLOW_WRITE=true to allow)")

    try:
        engine = create_engine(target_db_url, future=True)
        with engine.connect() as conn:
            result = conn.execute(text(sql_code))
            # SELECT 계열은 rows, 그 외는 rowcount
            if result.returns_rows:
                rows = _normalize_rows(result)
            else:
                conn.commit()
                rows = [{"rowcount": int(result.rowcount or 0)}]
    except Exception as exc:
        raise TaskExecutionError(f"sql execution failed: {exc}") from exc

    fmt = (output_format or "json").lower()
    summary = f"SQL task executed (rows={len(rows)})"

    if fmt == "csv":
        if rows:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
            csv_text = output.getvalue()
        else:
            csv_text = ""
        return {
            "summary": summary,
            "artifact_type": "csv",
            "content_text": csv_text,
            "content_json": json.dumps({"sql": sql_code, "rows": rows}, ensure_ascii=False),
            "content_html": None,
        }

    if fmt == "text":
        text_lines = [json.dumps(row, ensure_ascii=False) for row in rows]
        return {
            "summary": summary,
            "artifact_type": "text",
            "content_text": "\n".join(text_lines),
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
