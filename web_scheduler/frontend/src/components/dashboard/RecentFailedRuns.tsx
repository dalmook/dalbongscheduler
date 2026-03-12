import type { DashboardSummary } from "../../types/dashboard";

function RecentFailedRuns({ summary }: { summary: DashboardSummary }) {
  return (
    <div className="card">
      <h3>Recent Failed Runs</h3>
      {summary.recent_failed_runs.length === 0 ? (
        <div className="muted">No recent failures.</div>
      ) : (
        <ul>
          {summary.recent_failed_runs.map((row) => (
            <li key={row.run_id}>
              run #{row.run_id} task #{row.task_id} ({row.task_name}) - {row.error_message ?? "unknown error"}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default RecentFailedRuns;
