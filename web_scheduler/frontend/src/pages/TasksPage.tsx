import { useEffect, useState } from "react";
import { createTask, listTasks, removeTask, runTask, updateTask } from "../api/tasks";
import type { Task, TaskCreatePayload } from "../types/task";
import TaskTable from "../components/tasks/TaskTable";
import TaskFormModal from "../components/tasks/TaskFormModal";
import Loading from "../components/common/Loading";
import ErrorState from "../components/common/ErrorState";
import EmptyState from "../components/common/EmptyState";
import ConfirmDialog from "../components/common/ConfirmDialog";

function TasksPage() {
  const [rows, setRows] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [name, setName] = useState("");
  const [taskType, setTaskType] = useState("");
  const [enabled, setEnabled] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [targetDelete, setTargetDelete] = useState<Task | null>(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listTasks({ name: name || undefined, task_type: taskType || undefined, is_enabled: enabled || undefined });
      setRows(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const handleSave = async (payload: TaskCreatePayload) => {
    try {
      if (editing) {
        await updateTask(editing.id, payload);
        setMessage("Task updated");
      } else {
        await createTask(payload);
        setMessage("Task created");
      }
      setModalOpen(false);
      setEditing(null);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleRun = async (task: Task) => {
    try {
      const res = await runTask(task.id);
      setMessage(`Run created: ${res.run_id} (${res.status})`);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const askDelete = (task: Task) => {
    setTargetDelete(task);
    setConfirmOpen(true);
  };

  const confirmDelete = async () => {
    if (!targetDelete) return;
    try {
      await removeTask(targetDelete.id);
      setMessage("Task deleted");
      setConfirmOpen(false);
      setTargetDelete(null);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="stack">
      <h1>Tasks</h1>
      {message && <div className="state">{message}</div>}
      {error && <ErrorState message={error} />}

      <div className="row">
        <input className="input" placeholder="name" value={name} onChange={(e) => setName(e.target.value)} />
        <select className="input" value={taskType} onChange={(e) => setTaskType(e.target.value)}>
          <option value="">all types</option>
          <option value="python">python</option>
          <option value="sql">sql</option>
          <option value="html">html</option>
        </select>
        <select className="input" value={enabled} onChange={(e) => setEnabled(e.target.value)}>
          <option value="">all enabled</option>
          <option value="true">enabled</option>
          <option value="false">disabled</option>
        </select>
        <button className="btn" onClick={load}>Search</button>
        <button className="btn primary" onClick={() => { setEditing(null); setModalOpen(true); }}>New Task</button>
      </div>

      {loading ? <Loading /> : rows.length === 0 ? <EmptyState text="No tasks" /> : (
        <TaskTable
          rows={rows}
          onRun={handleRun}
          onEdit={(t) => { setEditing(t); setModalOpen(true); }}
          onDelete={askDelete}
        />
      )}

      <TaskFormModal open={modalOpen} initial={editing} onClose={() => { setModalOpen(false); setEditing(null); }} onSubmit={handleSave} />
      <ConfirmDialog
        open={confirmOpen}
        title="Delete Task"
        message={`Delete '${targetDelete?.name ?? ""}'?`}
        onConfirm={confirmDelete}
        onCancel={() => { setConfirmOpen(false); setTargetDelete(null); }}
      />
    </div>
  );
}

export default TasksPage;
