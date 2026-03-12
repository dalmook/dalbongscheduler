import { useEffect, useState } from "react";
import { fetchDashboardHtmlResults } from "../api/dashboard";
import { fetchTaskArtifacts } from "../api/tasks";
import HtmlPreviewPanel from "../components/artifacts/HtmlPreviewPanel";
import ErrorState from "../components/common/ErrorState";
import Loading from "../components/common/Loading";
import StatusBadge from "../components/common/StatusBadge";
import type { ArtifactListItem } from "../types/artifact";
import type { DashboardHtmlResult } from "../types/dashboard";

function HtmlResultsPage() {
  const [rows, setRows] = useState<DashboardHtmlResult[]>([]);
  const [versions, setVersions] = useState<ArtifactListItem[]>([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDashboardHtmlResults()
      .then((res) => setRows(res))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const openPreview = async (taskId: number, artifactId: number | null | undefined) => {
    if (!artifactId) return;
    setSelectedArtifactId(artifactId);
    try {
      const list = await fetchTaskArtifacts(taskId);
      setVersions(list.filter((item) => item.artifact_type === "html"));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="page-grid two-col">
      <section>
        <h1>HTML Results</h1>
        <table className="table">
          <thead>
            <tr>
              <th>Task</th>
              <th>Status</th>
              <th>Generated</th>
              <th>Preview text</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.task_id}>
                <td>{row.task_name}</td>
                <td><StatusBadge value={row.latest_run_status} /></td>
                <td>{row.latest_generated_at ?? "-"}</td>
                <td>{row.preview_text ?? "-"}</td>
                <td>{row.latest_artifact_id && <button className="btn" onClick={() => openPreview(row.task_id, row.latest_artifact_id)}>Preview</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <h3>HTML Artifact Versions</h3>
        <ul>
          {versions.map((item) => (
            <li key={item.id}>
              #{item.id} v{item.version_no} ({item.created_at}) <button className="btn" onClick={() => setSelectedArtifactId(item.id)}>Open</button>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Preview</h2>
        <HtmlPreviewPanel artifactId={selectedArtifactId} />
      </section>
    </div>
  );
}

export default HtmlResultsPage;
