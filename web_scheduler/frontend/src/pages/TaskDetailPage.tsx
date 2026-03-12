import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchTask, fetchTaskArtifacts, fetchTaskRuns, runTask } from "../api/tasks";
import ArtifactTable from "../components/artifacts/ArtifactTable";
import HtmlPreviewPanel from "../components/artifacts/HtmlPreviewPanel";
import ErrorState from "../components/common/ErrorState";
import Loading from "../components/common/Loading";
import RunTable from "../components/runs/RunTable";
import type { ArtifactListItem } from "../types/artifact";
import type { Run } from "../types/run";
import type { Task } from "../types/task";

function TaskDetailPage() {
  const { taskId } = useParams();
  const numericTaskId = Number(taskId);

  const [task, setTask] = useState<Task | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactListItem[]>([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [taskRes, runsRes, artifactsRes] = await Promise.all([
        fetchTask(numericTaskId),
        fetchTaskRuns(numericTaskId),
        fetchTaskArtifacts(numericTaskId),
      ]);
      setTask(taskRes);
      setRuns(runsRes);
      setArtifacts(artifactsRes);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!Number.isNaN(numericTaskId)) {
      void load();
    }
  }, [numericTaskId]);

  const onRun = async () => {
    await runTask(numericTaskId);
    await load();
  };

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;
  if (!task) return <ErrorState message="Task not found" />;

  return (
    <div className="page-grid">
      <h1>Task #{task.id} - {task.name}</h1>
      <div className="card">
        <div>type: {task.task_type}</div>
        <div>schedule: {task.schedule_type}</div>
        <div>enabled: {String(task.is_enabled)}</div>
        <div>next_run_at: {task.next_run_at ?? "-"}</div>
        <button className="btn" onClick={onRun}>Run Now</button>
      </div>

      <div className="card">
        <h3>Code</h3>
        <pre>{task.python_code ?? task.sql_code ?? task.html_template ?? "(no code)"}</pre>
      </div>

      <h2>Runs</h2>
      <RunTable runs={runs} onSelect={() => {}} />

      <h2>Artifacts</h2>
      <ArtifactTable artifacts={artifacts} onPreview={setSelectedArtifactId} />
      <HtmlPreviewPanel artifactId={selectedArtifactId} />
    </div>
  );
}

export default TaskDetailPage;
