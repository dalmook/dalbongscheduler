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
        <h1>Task #{task.id}</h1>
        <button className="btn" onClick={() => navigate("/tasks")}>Back</button>
      </div>
      <div className="card">
        <p><b>name:</b> {task.name}</p>
        <p><b>type:</b> {task.task_type}</p>
        <p><b>schedule:</b> {task.schedule_type}</p>
        <p><b>timezone:</b> {task.timezone ?? "-"}</p>
        <p><b>next_run_at:</b> {task.next_run_at ?? "-"}</p>
        <button className="btn primary" onClick={execute}>Run Now</button>
      </div>

      <div className="card">
        <h3>Code</h3>
        <pre>{task.python_code || task.sql_code || task.html_template || "(none)"}</pre>
      </div>

      <h3>Runs</h3>
      <RunTable rows={runs} onDetail={() => {}} />

      <h3>Artifacts</h3>
      <ArtifactTable rows={artifacts} onPreview={setSelectedArtifact} />
      <HtmlPreviewPanel artifact={selectedArtifact} />
    </div>
  );
}

export default TaskDetailPage;
