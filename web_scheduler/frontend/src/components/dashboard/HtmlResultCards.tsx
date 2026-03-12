import type { DashboardHtmlResult } from "../../types/dashboard";
import StatusBadge from "../common/StatusBadge";

function HtmlResultCards({ rows, onPreview }: { rows: DashboardHtmlResult[]; onPreview: (artifactId: number) => void }) {
  return (
    <div className="cards-grid">
      {rows.map((row) => {
        const artifactId = row.latest_artifact_id;
        return (
          <div key={row.task_id} className="card">
            <h4>{row.task_name}</h4>
            <StatusBadge value={row.latest_run_status} />
            <div className="muted">latest: {row.latest_generated_at ?? "-"}</div>
            <p>{row.preview_text ?? "(empty)"}</p>
            {artifactId != null && (
              <button className="btn" onClick={() => onPreview(artifactId)}>
                Preview
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default HtmlResultCards;
