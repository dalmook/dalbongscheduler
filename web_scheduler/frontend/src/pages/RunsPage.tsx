import { useEffect, useState } from "react";
import { fetchRun, fetchRuns } from "../api/runs";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import Loading from "../components/common/Loading";
import RunTable from "../components/runs/RunTable";
import type { Run } from "../types/run";

function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [taskIdFilter, setTaskIdFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [triggerTypeFilter, setTriggerTypeFilter] = useState("");

  const loadRuns = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchRuns({
        task_id: taskIdFilter || undefined,
        status: statusFilter || undefined,
        trigger_type: triggerTypeFilter || undefined,
      });
      setRuns(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRuns();
  }, []);

  const handleSelectRun = async (run: Run) => {
    try {
      const detail = await fetchRun(run.id);
      setSelectedRun(detail);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="page-grid">
      <h1>Runs</h1>
      <div className="toolbar">
        <input className="input" placeholder="task_id" value={taskIdFilter} onChange={(e) => setTaskIdFilter(e.target.value)} />
        <select className="input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">all status</option>
          <option value="queued">queued</option>
          <option value="running">running</option>
          <option value="success">success</option>
          <option value="failed">failed</option>
        </select>
        <select className="input" value={triggerTypeFilter} onChange={(e) => setTriggerTypeFilter(e.target.value)}>
          <option value="">all trigger</option>
          <option value="manual">manual</option>
          <option value="scheduled">scheduled</option>
        </select>
        <button className="btn" onClick={loadRuns}>Search</button>
      </div>

      {error && <ErrorState message={error} />}
      {loading ? <Loading /> : runs.length ? <RunTable runs={runs} onSelect={handleSelectRun} /> : <EmptyState message="No runs found" />}

      {selectedRun && (
        <div className="card">
          <h3>Run Detail #{selectedRun.id}</h3>
          <p>result_summary: {selectedRun.result_summary ?? "-"}</p>
          <p>error_message: {selectedRun.error_message ?? "-"}</p>
        </div>
      )}
    </div>
  );
}

export default RunsPage;
