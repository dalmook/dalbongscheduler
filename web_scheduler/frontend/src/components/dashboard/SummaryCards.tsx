import type { DashboardSummary } from "../../types/dashboard";

function SummaryCards({ summary }: { summary: DashboardSummary }) {
  const cards = [
    ["Total Tasks", summary.total_tasks],
    ["Enabled", summary.enabled_tasks],
    ["Scheduled", summary.scheduled_tasks],
    ["Success(24h)", summary.success_runs_24h],
    ["Failed(24h)", summary.failed_runs_24h],
    ["HTML Artifacts(24h)", summary.html_artifacts_24h],
  ];

  return (
    <div className="cards-grid">
      {cards.map(([label, value]) => (
        <div key={label} className="card">
          <div className="card-label">{label}</div>
          <div className="card-value">{value}</div>
        </div>
      ))}
    </div>
  );
}

export default SummaryCards;
