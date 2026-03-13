import json
import tempfile
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import TaskDefinition, TaskRun
from app.runners.html_runner import run_html_task
from app.runners.python_runner import run_python_task
from app.runners.sql_runner import run_sql_task
from app.services.artifact_service import create_artifact
from app.services.exceptions import (
    InvalidParamsJsonError,
    TaskExecutionError,
    TaskRunNotFoundError,
    UnsupportedTaskTypeError,
)
from app.services.notification_service import send_mail_html
from app.services.task_service import TaskNotFoundError, get_task

logger = get_logger(__name__)


def _as_utc(dt: datetime) -> datetime:
    """Normalize DB datetime values for safe subtraction on SQLite.

    SQLite often returns naive datetimes even when timezone-aware columns are used.
    """

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_run_record(db: Session, task_id: int, trigger_type: str = "manual") -> TaskRun:
    run = TaskRun(task_id=task_id, trigger_type=trigger_type, status="queued")
    db.add(run)
    db.flush()
    return run


def mark_run_running(db: Session, run: TaskRun) -> TaskRun:
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    db.flush()
    return run


def mark_run_success(db: Session, run: TaskRun, result_summary: str | None = None) -> TaskRun:
    finished_at = datetime.now(timezone.utc)
    run.status = "success"
    run.finished_at = finished_at
    run.result_summary = result_summary
    if run.started_at:
        run.duration_ms = int((finished_at - _as_utc(run.started_at)).total_seconds() * 1000)
    db.flush()
    return run


def mark_run_failed(db: Session, run: TaskRun, error_message: str) -> TaskRun:
    finished_at = datetime.now(timezone.utc)
    run.status = "failed"
    run.error_message = error_message
    run.finished_at = finished_at
    if run.started_at:
        run.duration_ms = int((finished_at - _as_utc(run.started_at)).total_seconds() * 1000)
    db.flush()
    return run


def _run_python_blocks_if_any(task: TaskDefinition) -> dict[str, str | None] | None:
    if task.task_type != "python" or not task.params_json:
        return None
    try:
        params = json.loads(task.params_json)
    except Exception:
        return None
    blocks = params.get("python_blocks") if isinstance(params, dict) else None
    if not isinstance(blocks, list) or not blocks:
        return None

    sections: list[str] = []
    for i, b in enumerate(blocks, start=1):
        if not isinstance(b, dict):
            continue
        title = str(b.get("title") or f"python_block_{i}")
        code = str(b.get("code") or "").strip()
        if not code:
            continue
        out = run_python_task(code, task.params_json)
        html = out.get("content_html") or f"<pre>{out.get('content_text') or out.get('summary') or ''}</pre>"
        sections.append(f"<section><h2>{title}</h2>{html}</section>")

    if not sections:
        return None

    combined_html = "<html><body>" + "<hr/>".join(sections) + "</body></html>"
    return {
        "summary": f"Python block mode executed ({len(sections)} sections)",
        "artifact_type": "html",
        "content_text": None,
        "content_json": json.dumps({"mode": "python_blocks", "count": len(sections)}, ensure_ascii=False),
        "content_html": combined_html,
    }


def _execute_by_task_type(task: TaskDefinition) -> dict[str, str | None]:
    block_mode_result = _run_block_mode_if_any(task)
    if block_mode_result is not None:
        return block_mode_result

    py_block_result = _run_python_blocks_if_any(task)
    if py_block_result is not None:
        return py_block_result

    if task.task_type == "python":
        return run_python_task(task.python_code, task.params_json)
    if task.task_type == "sql":
        return run_sql_task(task.sql_code, task.output_format)
    if task.task_type == "html":
        return run_html_task(task.html_template, task.params_json)

    raise UnsupportedTaskTypeError(f"Unsupported task type: {task.task_type}")


def _runtime_vars() -> dict[str, str]:
    now = datetime.now()
    return {
        "now": now.strftime("%Y-%m-%d %H:%M:%S"),
        "today": now.strftime("%Y-%m-%d"),
        "ymd": now.strftime("%Y%m%d"),
        "md": f"{now.month}/{now.day}",
    }


def _render_text_template(text: str, vars_map: dict[str, str]) -> str:
    out = text or ""
    for k, v in vars_map.items():
        out = out.replace("{" + str(k) + "}", str(v))
    return out


def _extract_mail_options(task: TaskDefinition) -> tuple[bool, str | None, str | None]:
    if not task.params_json:
        return False, None, None
    try:
        params = json.loads(task.params_json)
    except Exception:
        return False, None, None
    if not isinstance(params, dict):
        return False, None, None

    send = bool(params.get("mail_send", False))
    subject_tpl = params.get("mail_subject") if isinstance(params.get("mail_subject"), str) else None
    recipients_csv = params.get("mail_recipients") if isinstance(params.get("mail_recipients"), str) else None
    return send, subject_tpl, recipients_csv


def _build_sql_excel_attachment_if_any(task: TaskDefinition) -> list[str]:
    """Build one or more excel attachments from SQL definitions.

    Sources:
    - task.sql_code (single sql)
    - params_json.sql_attachment_blocks: [{title, sql}]
    """
    from app.core.config import get_settings

    settings = get_settings()
    db_url = settings.sql_runner_database_url or settings.database_url
    rv = _runtime_vars()

    sql_jobs: list[tuple[str, str]] = []

    if task.sql_code and task.sql_code.strip():
        sql_jobs.append(("sql_attachment", _replace_tokens(task.sql_code, rv)))

    if task.params_json:
        try:
            params = json.loads(task.params_json)
            blocks = params.get("sql_attachment_blocks") if isinstance(params, dict) else None
            if isinstance(blocks, list):
                for i, b in enumerate(blocks, start=1):
                    if not isinstance(b, dict):
                        continue
                    title = str(b.get("title") or f"sql_block_{i}")
                    sql_raw = str(b.get("sql") or "").strip()
                    if sql_raw:
                        sql_jobs.append((title, _replace_tokens(sql_raw, rv)))
        except Exception:
            pass

    if not sql_jobs:
        return []

    attachments: list[str] = []
    for title, sql in sql_jobs:
        try:
            df = _query_to_dataframe(sql, db_url)
            tmp = tempfile.NamedTemporaryFile(prefix=f"task_{task.id}_{title}_", suffix=".xlsx", delete=False)
            tmp_path = tmp.name
            tmp.close()
            df.to_excel(tmp_path, index=False)
            attachments.append(tmp_path)
            logger.info("sql attachment built: task_id=%s title=%s rows=%s", task.id, title, len(df))
        except Exception as exc:
            logger.warning("sql attachment query/build failed: task_id=%s title=%s err=%s", task.id, title, exc)

    return attachments


def _replace_tokens(text_value: str | None, vars_map: dict[str, str]) -> str:
    out = text_value or ""
    for k, v in vars_map.items():
        out = out.replace("{" + str(k) + "}", str(v))
    return out


def _query_to_dataframe(sql_text: str, db_url: str) -> pd.DataFrame:
    engine = create_engine(db_url, future=True)
    with engine.connect() as conn:
        return pd.read_sql(text(sql_text), conn)


def _render_df_table_html(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "<p>(조회 결과 없음)</p>"
    return df.to_html(index=False, border=1, justify="center")


def _run_block_mode_if_any(task: TaskDefinition) -> dict[str, str | None] | None:
    if not task.params_json:
        return None
    try:
        params = json.loads(task.params_json)
    except Exception:
        return None
    if not isinstance(params, dict):
        return None

    sql_blocks = params.get("sql_blocks")
    if not isinstance(sql_blocks, list) or not sql_blocks:
        return None

    from app.core.config import get_settings

    settings = get_settings()
    db_url = settings.sql_runner_database_url or settings.database_url
    gvars = _runtime_vars()

    sections: list[str] = []
    block_rows: list[dict] = []

    for i, raw in enumerate(sql_blocks, start=1):
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or f"블록{i}")
        sql_tpl = str(raw.get("sql") or "").strip()
        sql = _replace_tokens(sql_tpl, gvars)
        html_tpl = str(raw.get("html_tpl") or "").strip()
        py_code = str(raw.get("py_code") or "").strip()

        if not sql:
            continue

        try:
            df = _query_to_dataframe(sql, db_url)
            block_rows.append({"title": title, "rows": len(df)})
            html_table = _render_df_table_html(df)

            body = html_tpl or "<h3>{title}</h3>{html_table}"
            body = body.replace("{title}", title).replace("{html_table}", html_table)
            body = _replace_tokens(body, gvars)

            # optional block python post-process: can override html via RESULT_HTML/html var
            if py_code:
                loc = {"df": df, "gvars": gvars, "html": body, "RESULT_HTML": None}
                exec(py_code, {"__builtins__": __builtins__}, loc)
                for key in ("RESULT_HTML", "result_html", "html"):
                    val = loc.get(key)
                    if isinstance(val, str) and val.strip():
                        body = val
                        break

            sections.append(f"<section><h2>{title}</h2>{body}</section>")
        except Exception as exc:
            sections.append(f"<section><h2>{title}</h2><pre>실행 오류: {exc}</pre></section>")

    if not sections:
        return None

    combined_html = "<html><body>" + "<hr/>".join(sections) + "</body></html>"
    payload_json = {"mode": "block", "blocks": block_rows}
    return {
        "summary": f"Block mode executed ({len(sections)} sections)",
        "artifact_type": "html",
        "content_text": None,
        "content_json": json.dumps(payload_json, ensure_ascii=False),
        "content_html": combined_html,
    }


def run_task(db: Session, task_id: int, trigger_type: str = "manual") -> TaskRun:
    try:
        task = get_task(db, task_id)
    except TaskNotFoundError:
        raise

    run = create_run_record(db, task_id=task.id, trigger_type=trigger_type)
    db.commit()

    try:
        mark_run_running(db, run)
        db.commit()

        result = _execute_by_task_type(task)

        create_artifact(
            db,
            task_id=task.id,
            run_id=run.id,
            artifact_type=(result.get("artifact_type") or "text"),
            content_text=result.get("content_text"),
            content_html=result.get("content_html"),
            content_json=result.get("content_json"),
        )

        mark_run_success(db, run, result.get("summary"))
        task.last_run_status = "success"
        task.last_run_at = datetime.now(timezone.utc)

        # optional mail delivery (legacy scheduler-like behavior)
        mail_send, subject_tpl, recipients_csv = _extract_mail_options(task)
        if mail_send:
            rv = _runtime_vars()
            default_subject = f"[{rv['md']}] {task.name}"
            subject = _render_text_template(subject_tpl or default_subject, rv)
            html_body = result.get("content_html") or f"<html><body><pre>{result.get('content_text') or result.get('summary') or ''}</pre></body></html>"

            attachments: list[str] = []
            if task.task_type in {"python", "html"}:
                attachments = _build_sql_excel_attachment_if_any(task)

            try:
                send_mail_html(subject=subject, html_body=html_body, recipients_csv=recipients_csv, attachments=attachments)
            finally:
                for p in attachments:
                    try:
                        import os
                        if p and os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass

        db.commit()
        db.refresh(run)
        logger.info("Task run success: task_id=%s run_id=%s", task.id, run.id)
        return run

    except (TaskExecutionError, InvalidParamsJsonError, UnsupportedTaskTypeError) as exc:
        mark_run_failed(db, run, str(exc))
        task.last_run_status = "failed"
        task.last_run_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        logger.exception("Task run failed: task_id=%s run_id=%s", task.id, run.id)
        raise
    except Exception as exc:
        mark_run_failed(db, run, str(exc))
        task.last_run_status = "failed"
        task.last_run_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        logger.exception("Unexpected execution error: task_id=%s run_id=%s", task.id, run.id)
        raise TaskExecutionError(str(exc)) from exc


def list_runs(
    db: Session,
    *,
    task_id: int | None = None,
    status: str | None = None,
    trigger_type: str | None = None,
) -> list[TaskRun]:
    stmt = select(TaskRun)
    if task_id is not None:
        stmt = stmt.where(TaskRun.task_id == task_id)
    if status:
        stmt = stmt.where(TaskRun.status == status)
    if trigger_type:
        stmt = stmt.where(TaskRun.trigger_type == trigger_type)

    return list(db.execute(stmt.order_by(TaskRun.created_at.desc())).scalars().all())


def get_run(db: Session, run_id: int) -> TaskRun:
    run = db.get(TaskRun, run_id)
    if not run:
        raise TaskRunNotFoundError("Run not found")
    return run
