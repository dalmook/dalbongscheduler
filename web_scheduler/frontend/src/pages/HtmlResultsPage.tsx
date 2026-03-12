import { useEffect, useMemo, useState } from "react";
import { listArtifacts } from "../api/artifacts";
import type { Artifact } from "../types/artifact";
import Loading from "../components/common/Loading";
import ErrorState from "../components/common/ErrorState";
import EmptyState from "../components/common/EmptyState";
import ArtifactTable from "../components/artifacts/ArtifactTable";
import HtmlPreviewPanel from "../components/artifacts/HtmlPreviewPanel";

function HtmlResultsPage() {
  const [rows, setRows] = useState<Artifact[]>([]);
  const [taskId, setTaskId] = useState("");
  const [selected, setSelected] = useState<Artifact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listArtifacts({ task_id: taskId || undefined });
      setRows(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const filtered = useMemo(() => rows.filter((a) => a.artifact_type === "html" || a.artifact_type === "json" || a.artifact_type === "text"), [rows]);

  return (
    <div className="stack two-col">
      <section className="stack">
        <h1>HTML Results</h1>
        {error && <ErrorState message={error} />}
        <div className="row">
          <input className="input" placeholder="task_id" value={taskId} onChange={(e) => setTaskId(e.target.value)} />
          <button className="btn" onClick={load}>Search</button>
        </div>

        {loading ? <Loading /> : filtered.length ? <ArtifactTable rows={filtered} onPreview={setSelected} /> : <EmptyState text="No artifacts" />}
      </section>
      <section className="stack">
        <h2>Preview</h2>
        <HtmlPreviewPanel artifact={selected} />
      </section>
    </div>
  );
}

export default HtmlResultsPage;
