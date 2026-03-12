import { useEffect, useMemo, useState } from "react";
import { createTask, deleteTask, fetchTasks, runTask, updateTask } from "../api/tasks";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import Loading from "../components/common/Loading";
import SearchBar from "../components/common/SearchBar";
import TaskFormModal from "../components/tasks/TaskFormModal";
import TaskTable from "../components/tasks/TaskTable";
import type { Task, TaskCreatePayload } from "../types/task";

function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [nameFilter, setNameFilter] = useState("");
  const [taskTypeFilter, setTaskTypeFilter] = useState("");
  const [enabledFilter, setEnabledFilter] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  const loadTasks = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchTasks({
        name: nameFilter || undefined,
        task_type: taskTypeFilter || undefined,
        is_enabled: enabledFilter || undefined,
      });
      setTasks(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadTasks();
  }, []);

  const filteredTasks = useMemo(() => tasks, [tasks]);

  const handleSubmitForm = async (payload: TaskCreatePayload) => {
    try {
      if (editingTask) {
        await updateTask(editingTask.id, payload);
        setMessage("Task updated");
      } else {
        await createTask(payload);
        setMessage("Task created");
      }
      setModalOpen(false);
      setEditingTask(null);
      await loadTasks();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleRun = async (taskId: number) => {
    try {
      const res = await runTask(taskId);
      setMessage(`Run started: #${res.run_id} (${res.status})`);
      await loadTasks();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleDelete = async (task: Task) => {
    if (!window.confirm(`Delete task '${task.name}'?`)) return;
    try {
      await deleteTask(task.id);
      setMessage("Task deleted");
      await loadTasks();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="page-grid">
      <h1>Tasks</h1>
      {message && <div className="state-box">{message}</div>}
      {error && <ErrorState message={error} />}

      <div className="toolbar">
        <SearchBar value={nameFilter} onChange={setNameFilter} placeholder="search by name" />
        <select className="input" value={taskTypeFilter} onChange={(e) => setTaskTypeFilter(e.target.value)}>
          <option value="">all types</option>
          <option value="python">python</option>
          <option value="sql">sql</option>
          <option value="html">html</option>
        </select>
        <select className="input" value={enabledFilter} onChange={(e) => setEnabledFilter(e.target.value)}>
          <option value="">all enabled</option>
          <option value="true">enabled</option>
          <option value="false">disabled</option>
        </select>
        <button className="btn" onClick={loadTasks}>Search</button>
        <button className="btn primary" onClick={() => { setEditingTask(null); setModalOpen(true); }}>New Task</button>
      </div>

      {loading ? <Loading /> : filteredTasks.length ? <TaskTable tasks={filteredTasks} onRun={handleRun} onEdit={(task) => { setEditingTask(task); setModalOpen(true); }} onDelete={handleDelete} /> : <EmptyState message="No tasks found" />}

      <TaskFormModal open={modalOpen} initialTask={editingTask} onClose={() => { setModalOpen(false); setEditingTask(null); }} onSubmit={handleSubmitForm} />
    </div>
  );
}

export default TasksPage;
