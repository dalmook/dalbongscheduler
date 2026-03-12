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

  useEffect(() => {
    void load();
  }, []);

  const handleSave = async (payload: TaskCreatePayload) => {
    try {
      if (editing) {
        await updateTask(editing.id, payload);
        setMessage("작업이 수정되었습니다.");
      } else {
        await createTask(payload);
        setMessage("작업이 생성되었습니다.");
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
      setMessage(`실행 생성 완료: run_id=${res.run_id}, status=${res.status}`);
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
      setMessage("작업이 삭제되었습니다.");
      setConfirmOpen(false);
      setTargetDelete(null);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="stack">
      <h1>작업 관리</h1>
      {message && <div className="state">{message}</div>}
      {error && <ErrorState message={error} />}

      <div className="row">
        <input className="input" placeholder="작업명" value={name} onChange={(e) => setName(e.target.value)} />
        <select className="input" value={taskType} onChange={(e) => setTaskType(e.target.value)}>
          <option value="">전체 유형</option>
          <option value="python">파이썬</option>
          <option value="sql">SQL</option>
          <option value="html">HTML</option>
        </select>
        <select className="input" value={enabled} onChange={(e) => setEnabled(e.target.value)}>
          <option value="">전체 상태</option>
          <option value="true">사용중</option>
          <option value="false">중지</option>
        </select>
        <button className="btn" onClick={load}>조회</button>
        <button
          className="btn primary"
          onClick={() => {
            setEditing(null);
            setModalOpen(true);
          }}
        >
          새 작업
        </button>
      </div>

      {loading ? (
        <Loading />
      ) : rows.length === 0 ? (
        <EmptyState text="등록된 작업이 없습니다." />
      ) : (
        <TaskTable
          rows={rows}
          onRun={handleRun}
          onEdit={(t) => {
            setEditing(t);
            setModalOpen(true);
          }}
          onDelete={askDelete}
        />
      )}

      <TaskFormModal
        open={modalOpen}
        initial={editing}
        onClose={() => {
          setModalOpen(false);
          setEditing(null);
        }}
        onSubmit={handleSave}
      />
      <ConfirmDialog
        open={confirmOpen}
        title="작업 삭제"
        message={`'${targetDelete?.name ?? ""}' 작업을 삭제할까요?`}
        onConfirm={confirmDelete}
        onCancel={() => {
          setConfirmOpen(false);
          setTargetDelete(null);
        }}
      />
    </div>
  );
}

export default TasksPage;
