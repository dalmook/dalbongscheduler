import type { DashboardHtmlResult } from "../../types/dashboard";
import StatusBadge from "../common/StatusBadge";

function HtmlResultCards({ rows, onPreview }: { rows: DashboardHtmlResult[]; onPreview: (artifactId: number) => void }) {
  return (
    <div className="cards-grid">
      {rows.map((row) => (
        <div key={row.task_id} className="card">
          <h4>{row.task_name}</h4>
          <StatusBadge value={row.latest_run_status} />
          <div className="muted">latest: {row.latest_generated_at ?? "-"}</div>
          <p>{row.preview_text ?? "(empty)"}</p>
          {row.latest_artifact_id && <button className="btn" onClick={() => onPreview(row.latest_artifact_id)}>Preview</button>}
        </div>
      ))}
    </div>
  );
}

export default HtmlResultCards;
