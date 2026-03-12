import { useEffect, useMemo, useState } from "react";
import { getHealth } from "../api/health";
import { listTasks } from "../api/tasks";
import { listRuns } from "../api/runs";
import { listArtifacts } from "../api/artifacts";
import type { HealthResponse } from "../types/common";
import type { Task } from "../types/task";
import type { Run } from "../types/run";
import type { Artifact } from "../types/artifact";
import Loading from "../components/common/Loading";
import ErrorState from "../components/common/ErrorState";
import EmptyState from "../components/common/EmptyState";
import StatusBadge from "../components/common/StatusBadge";

function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getHealth(), listTasks(), listRuns(), listArtifacts()])
      .then(([h, t, r, a]) => {
        setHealth(h);
        setTasks(t);
        setRuns(r);
        setArtifacts(a);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const stats = useMemo(() => {
    const success = runs.filter((r) => r.status === "success").length;
    const failed = runs.filter((r) => r.status === "failed").length;
    const enabled = tasks.filter((t) => t.is_enabled).length;
    const htmlRecent = artifacts.filter((a) => a.artifact_type === "html").slice(0, 5);
    return { success, failed, enabled, htmlRecent };
  }, [tasks, runs, artifacts]);

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="stack">
      <h1>Dashboard</h1>
      <div className="cards">
        <div className="card"><div className="muted">health</div><b>{health?.status ?? "unknown"}</b></div>
        <div className="card"><div className="muted">total tasks</div><b>{tasks.length}</b></div>
        <div className="card"><div className="muted">enabled tasks</div><b>{stats.enabled}</b></div>
        <div className="card"><div className="muted">success runs</div><b>{stats.success}</b></div>
        <div className="card"><div className="muted">failed runs</div><b>{stats.failed}</b></div>
      </div>

      <section className="card">
        <h3>Recent Runs (5)</h3>
        {runs.length === 0 ? <EmptyState text="No runs" /> : (
          <ul>
            {runs.slice(0, 5).map((r) => (
              <li key={r.id}>#{r.id} task #{r.task_id} <StatusBadge value={r.status} /></li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h3>Recent HTML Artifacts (5)</h3>
        {stats.htmlRecent.length === 0 ? <EmptyState text="No html artifacts" /> : (
          <ul>
            {stats.htmlRecent.map((a) => (
              <li key={a.id}>artifact #{a.id} (task #{a.task_id})</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default DashboardPage;
