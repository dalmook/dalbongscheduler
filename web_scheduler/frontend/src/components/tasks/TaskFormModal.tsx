import { useEffect, useState } from "react";
import type { Task, TaskCreatePayload } from "../../types/task";

interface Props {
  open: boolean;
  initialTask?: Task | null;
  onClose: () => void;
  onSubmit: (payload: TaskCreatePayload) => Promise<void>;
}

const DEFAULT_FORM: TaskCreatePayload = {
  name: "",
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

function TaskFormModal({ open, initialTask, onClose, onSubmit }: Props) {
  const [form, setForm] = useState<TaskCreatePayload>(DEFAULT_FORM);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (initialTask) {
      setForm({
        ...DEFAULT_FORM,
        ...initialTask,
        description: initialTask.description ?? "",
        cron_expr: initialTask.cron_expr ?? "",
        interval_seconds: initialTask.interval_seconds ?? undefined,
        params_json: initialTask.params_json ?? "",
        python_code: initialTask.python_code ?? "",
        sql_code: initialTask.sql_code ?? "",
        html_template: initialTask.html_template ?? "",
      });
    } else {
      setForm(DEFAULT_FORM);
    }
    setError("");
  }, [initialTask, open]);

  if (!open) return null;

  const validate = () => {
    if (!form.name.trim()) return "name is required";
    if (form.schedule_type === "cron" && !form.cron_expr) return "cron_expr is required";
    if (form.schedule_type === "interval" && (!form.interval_seconds || form.interval_seconds < 10)) {
      return "interval_seconds must be >= 10";
    }
    if (form.params_json) {
      try {
        JSON.parse(form.params_json);
      } catch {
        return "params_json must be valid JSON";
      }
    }
    return "";
  };

  const handleSubmit = async () => {
    const msg = validate();
    if (msg) {
      setError(msg);
      return;
    }
    await onSubmit(form);
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h3>{initialTask ? "Edit Task" : "Create Task"}</h3>
        {error && <div className="state-box error">{error}</div>}
        <div className="grid-two">
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
            <input className="input" placeholder="cron expr (*/5 * * * *)" value={form.cron_expr ?? ""} onChange={(e) => setForm({ ...form, cron_expr: e.target.value })} />
          )}
          {form.schedule_type === "interval" && (
            <input className="input" type="number" placeholder="interval seconds" value={form.interval_seconds ?? ""} onChange={(e) => setForm({ ...form, interval_seconds: Number(e.target.value) })} />
          )}

          <select className="input" value={form.output_format ?? "json"} onChange={(e) => setForm({ ...form, output_format: e.target.value })}>
            <option value="json">json</option>
            <option value="text">text</option>
            <option value="html">html</option>
            <option value="csv">csv</option>
          </select>

          <label className="checkbox-row">
            <input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })} /> enabled
          </label>
        </div>

        <textarea className="textarea" placeholder="params_json" value={form.params_json ?? ""} onChange={(e) => setForm({ ...form, params_json: e.target.value })} />

        {form.task_type === "python" && <textarea className="textarea code" placeholder="python_code" value={form.python_code ?? ""} onChange={(e) => setForm({ ...form, python_code: e.target.value })} />}
        {form.task_type === "sql" && <textarea className="textarea code" placeholder="sql_code" value={form.sql_code ?? ""} onChange={(e) => setForm({ ...form, sql_code: e.target.value })} />}
        {form.task_type === "html" && <textarea className="textarea code" placeholder="html_template" value={form.html_template ?? ""} onChange={(e) => setForm({ ...form, html_template: e.target.value })} />}

        <div className="actions right">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={handleSubmit}>Save</button>
        </div>
      </div>
    </div>
  );
}

export default TaskFormModal;
