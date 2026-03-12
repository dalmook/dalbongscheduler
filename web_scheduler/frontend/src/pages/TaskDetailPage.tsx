import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getTask, listTaskArtifacts, listTaskRuns, runTask } from "../api/tasks";
import type { Task } from "../types/task";
import type { Run } from "../types/run";
import type { Artifact } from "../types/artifact";
import Loading from "../components/common/Loading";
import ErrorState from "../components/common/ErrorState";
import RunTable from "../components/runs/RunTable";
import ArtifactTable from "../components/artifacts/ArtifactTable";
import HtmlPreviewPanel from "../components/artifacts/HtmlPreviewPanel";

function TaskDetailPage() {
  const { taskId } = useParams();
  const id = Number(taskId);
  const navigate = useNavigate();

  const [task, setTask] = useState<Task | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [t, r, a] = await Promise.all([getTask(id), listTaskRuns(id), listTaskArtifacts(id)]);
      setTask(t);
      setRuns(r);
      setArtifacts(a);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (!Number.isNaN(id)) void load(); }, [id]);

  const execute = async () => {
    try {
      await runTask(id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;
  if (!task) return <ErrorState message="Task not found" />;

  return (
    <div className="stack">
      <div className="row between">
        <h1>작업 #{task.id}</h1>
        <button className="btn" onClick={() => navigate("/tasks")}>목록</button>
      </div>
      <div className="card">
        <p><b>이름:</b> {task.name}</p>
        <p><b>유형:</b> {task.task_type}</p>
        <p><b>스케줄:</b> {task.schedule_type}</p>
        <p><b>시간대:</b> {task.timezone ?? "-"}</p>
        <p><b>다음 실행:</b> {task.next_run_at ?? "-"}</p>
        <button className="btn primary" onClick={execute}>지금 실행</button>
      </div>

      <div className="card">
        <h3>코드</h3>
        <pre>{task.python_code || task.sql_code || task.html_template || "(none)"}</pre>
      </div>

      <h3>실행 이력</h3>
      <RunTable rows={runs} onDetail={() => {}} />

      <h3>결과물 (엑셀 다운로드 가능)</h3>
      <ArtifactTable rows={artifacts} onPreview={setSelectedArtifact} />
      <HtmlPreviewPanel artifact={selectedArtifact} />
    </div>
  );
}

export default TaskDetailPage;
