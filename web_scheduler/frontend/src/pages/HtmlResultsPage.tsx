import { useEffect, useMemo, useState } from "react";
import { getDashboardHtmlResults } from "../api/dashboard";
import { getArtifact, getArtifactPreviewUrl } from "../api/artifacts";
import type { Artifact } from "../types/artifact";
import type { DashboardHtmlResult } from "../types/dashboard";
import Loading from "../components/common/Loading";
import ErrorState from "../components/common/ErrorState";
import EmptyState from "../components/common/EmptyState";
import StatusBadge from "../components/common/StatusBadge";

function HtmlResultsPage() {
  const [rows, setRows] = useState<DashboardHtmlResult[]>([]);
  const [taskFilter, setTaskFilter] = useState("");
  const [selected, setSelected] = useState<Artifact | null>(null);
  const [selectedPreviewUrl, setSelectedPreviewUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getDashboardHtmlResults();
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

  const filtered = useMemo(() => {
    if (!taskFilter.trim()) return rows;
    const keyword = taskFilter.trim().toLowerCase();
    return rows.filter((item) => String(item.task_id).includes(keyword) || item.task_name.toLowerCase().includes(keyword));
  }, [rows, taskFilter]);

  const openPreview = async (artifactId?: number | null) => {
    if (!artifactId) return;
    try {
      const artifact = await getArtifact(artifactId);
      setSelected(artifact);
      setSelectedPreviewUrl(getArtifactPreviewUrl(artifactId));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="stack two-col">
      <section className="stack">
        <div className="row between">
          <h1>HTML Results</h1>
          <button className="btn" onClick={load}>Refresh</button>
        </div>
        {error && <ErrorState message={error} />}

        <div className="row">
          <input
            className="input"
            placeholder="filter by task id or name"
            value={taskFilter}
            onChange={(e) => setTaskFilter(e.target.value)}
          />
        </div>

        {loading ? <Loading /> : filtered.length === 0 ? <EmptyState text="No html result rows" /> : (
          <table className="table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Status</th>
                <th>Artifact</th>
                <th>Generated</th>
                <th>Preview Text</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.task_id}>
                  <td>{item.task_name} (#{item.task_id})</td>
                  <td><StatusBadge value={item.latest_run_status} /></td>
                  <td>{item.latest_artifact_id ?? "-"}</td>
                  <td>{item.latest_generated_at ?? "-"}</td>
                  <td>{item.preview_text ?? "-"}</td>
                  <td>
                    <button
                      className="btn"
                      disabled={!item.latest_artifact_id}
                      onClick={() => void openPreview(item.latest_artifact_id)}
                    >
                      Preview
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="stack">
        <h2>Preview</h2>
        {!selected ? <EmptyState text="Select a row to preview" /> : selected.artifact_type === "html" ? (
          <div className="preview-wrap">
            <iframe className="preview-iframe" src={selectedPreviewUrl} title="preview" />
          </div>
        ) : (
          <div className="card"><pre>{selected.content_text || selected.content_json || "(no preview content)"}</pre></div>
        )}
      </section>
    </div>
  );
}

export default HtmlResultsPage;
