import { useEffect, useState } from "react";
import { getRun, listRuns } from "../api/runs";
import type { Run } from "../types/run";
import Loading from "../components/common/Loading";
import ErrorState from "../components/common/ErrorState";
import EmptyState from "../components/common/EmptyState";
import RunTable from "../components/runs/RunTable";
import RunDetailModal from "../components/runs/RunDetailModal";

function RunsPage() {
  const [rows, setRows] = useState<Run[]>([]);
  const [selected, setSelected] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [taskId, setTaskId] = useState("");
  const [status, setStatus] = useState("");
  const [trigger, setTrigger] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listRuns({ task_id: taskId || undefined, status: status || undefined, trigger_type: trigger || undefined });
      setRows(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const openDetail = async (run: Run) => {
    try {
      const detail = await getRun(run.id);
      setSelected(detail);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="stack">
      <h1>Runs</h1>
      {error && <ErrorState message={error} />}
      <div className="row">
        <input className="input" placeholder="task_id" value={taskId} onChange={(e) => setTaskId(e.target.value)} />
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">all status</option>
          <option value="queued">queued</option>
          <option value="running">running</option>
          <option value="success">success</option>
          <option value="failed">failed</option>
        </select>
        <select className="input" value={trigger} onChange={(e) => setTrigger(e.target.value)}>
          <option value="">all trigger</option>
          <option value="manual">manual</option>
          <option value="scheduled">scheduled</option>
        </select>
        <button className="btn" onClick={load}>Search</button>
      </div>

      {loading ? <Loading /> : rows.length ? <RunTable rows={rows} onDetail={openDetail} /> : <EmptyState text="No runs" />}
      <RunDetailModal run={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

export default RunsPage;
