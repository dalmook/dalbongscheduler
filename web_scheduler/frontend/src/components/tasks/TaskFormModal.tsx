import { useEffect, useState } from "react";
import type { Task, TaskCreatePayload } from "../../types/task";

interface Props {
  open: boolean;
  initial?: Task | null;
  onClose: () => void;
  onSubmit: (payload: TaskCreatePayload) => Promise<void>;
}

const DEFAULT_PAYLOAD: TaskCreatePayload = {
  name: "",
  description: "",
  task_type: "python",
  schedule_type: "manual",
  is_enabled: true,
  timezone: "Asia/Seoul",
  python_code: "",
  sql_code: "",
  html_template: "",
  params_json: "",
  output_format: "json",
};

function TaskFormModal({ open, initial, onClose, onSubmit }: Props) {
  const [form, setForm] = useState<TaskCreatePayload>(DEFAULT_PAYLOAD);
  const [error, setError] = useState("");

  useEffect(() => {
    if (initial) {
      setForm({
        ...DEFAULT_PAYLOAD,
        ...initial,
        description: initial.description ?? "",
        cron_expr: initial.cron_expr ?? "",
        interval_seconds: initial.interval_seconds ?? undefined,
        python_code: initial.python_code ?? "",
        sql_code: initial.sql_code ?? "",
        html_template: initial.html_template ?? "",
        params_json: initial.params_json ?? "",
      });
    } else {
      setForm(DEFAULT_PAYLOAD);
    }
    setError("");
  }, [initial, open]);

  if (!open) return null;

  const validate = () => {
    if (!form.name.trim()) return "name is required";
    if (form.schedule_type === "cron" && !form.cron_expr?.trim()) return "cron_expr is required";
    if (form.schedule_type === "interval" && (!form.interval_seconds || form.interval_seconds <= 0)) {
      return "interval_seconds is required";
    }
    if (form.params_json?.trim()) {
      try {
        JSON.parse(form.params_json);
      } catch {
        return "params_json must be valid JSON";
      }
    }
    return "";
  };

  const submit = async () => {
    const msg = validate();
    if (msg) {
      setError(msg);
      return;
    }
    await onSubmit(form);
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>{initial ? "Edit Task" : "Create Task"}</h3>
        {error && <div className="state error">{error}</div>}

        <div className="grid-2">
          <input className="input" placeholder="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="input" placeholder="description" value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />

          <select className="input" value={form.task_type} onChange={(e) => setForm({ ...form, task_type: e.target.value as TaskCreatePayload["task_type"] })}>
            <option value="python">python</option>
            <option value="sql">sql</option>
            <option value="html">html</option>
          </select>

          <select className="input" value={form.schedule_type} onChange={(e) => setForm({ ...form, schedule_type: e.target.value as TaskCreatePayload["schedule_type"] })}>
            <option value="manual">manual</option>
            <option value="cron">cron</option>
            <option value="interval">interval</option>
          </select>

          {form.schedule_type === "cron" && (
            <input className="input" placeholder="cron_expr" value={form.cron_expr ?? ""} onChange={(e) => setForm({ ...form, cron_expr: e.target.value })} />
          )}
          {form.schedule_type === "interval" && (
            <input className="input" placeholder="interval_seconds" type="number" value={form.interval_seconds ?? ""} onChange={(e) => setForm({ ...form, interval_seconds: Number(e.target.value) })} />
          )}

          <select className="input" value={form.output_format ?? "json"} onChange={(e) => setForm({ ...form, output_format: e.target.value })}>
            <option value="json">json</option>
            <option value="text">text</option>
            <option value="html">html</option>
            <option value="csv">csv</option>
          </select>

          <label className="check">
            <input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })} /> enabled
          </label>
        </div>

        <textarea className="textarea" placeholder="params_json" value={form.params_json ?? ""} onChange={(e) => setForm({ ...form, params_json: e.target.value })} />

        {form.task_type === "python" && <textarea className="textarea code" placeholder="python_code" value={form.python_code ?? ""} onChange={(e) => setForm({ ...form, python_code: e.target.value })} />}
        {form.task_type === "sql" && <textarea className="textarea code" placeholder="sql_code" value={form.sql_code ?? ""} onChange={(e) => setForm({ ...form, sql_code: e.target.value })} />}
        {form.task_type === "html" && <textarea className="textarea code" placeholder="html_template" value={form.html_template ?? ""} onChange={(e) => setForm({ ...form, html_template: e.target.value })} />}

        <div className="row right">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={submit}>Save</button>
        </div>
      </div>
    </div>
  );
}

export default TaskFormModal;
