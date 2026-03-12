import { useEffect, useState } from "react";
import { getDashboardHtmlResults, getDashboardJobs, getDashboardSummary } from "../api/dashboard";
import type { DashboardHtmlResult, DashboardJob, DashboardSummary } from "../types/dashboard";
import Loading from "../components/common/Loading";
import ErrorState from "../components/common/ErrorState";
import EmptyState from "../components/common/EmptyState";
import StatusBadge from "../components/common/StatusBadge";

function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [jobs, setJobs] = useState<DashboardJob[]>([]);
  const [htmlResults, setHtmlResults] = useState<DashboardHtmlResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [summaryData, jobsData, htmlData] = await Promise.all([
        getDashboardSummary(),
        getDashboardJobs(),
        getDashboardHtmlResults(),
      ]);
      setSummary(summaryData);
      setJobs(jobsData);
      setHtmlResults(htmlData);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;
  if (!summary) return <EmptyState text="No dashboard data" />;

  return (
    <div className="stack">
      <div className="row between">
        <h1>Dashboard</h1>
        <button className="btn" onClick={load}>Refresh</button>
      </div>

      <div className="cards">
        <div className="card"><div className="muted">total tasks</div><b>{summary.total_tasks}</b></div>
        <div className="card"><div className="muted">enabled tasks</div><b>{summary.enabled_tasks}</b></div>
        <div className="card"><div className="muted">scheduled tasks</div><b>{summary.scheduled_tasks}</b></div>
        <div className="card"><div className="muted">running tasks</div><b>{summary.running_tasks}</b></div>
        <div className="card"><div className="muted">success runs (24h)</div><b>{summary.success_runs_24h}</b></div>
        <div className="card"><div className="muted">failed runs (24h)</div><b>{summary.failed_runs_24h}</b></div>
        <div className="card"><div className="muted">html artifacts (24h)</div><b>{summary.html_artifacts_24h}</b></div>
      </div>

      <section className="card">
        <h3>Scheduler Jobs</h3>
        {jobs.length === 0 ? <EmptyState text="No registered jobs" /> : (
          <table className="table">
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Task</th>
                <th>Trigger</th>
                <th>Next Run</th>
                <th>Enabled</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.job_id}>
                  <td>{job.job_id}</td>
                  <td>{job.task_name ?? `task #${job.task_id ?? "-"}`}</td>
                  <td>{job.trigger}</td>
                  <td>{job.next_run_time ?? "-"}</td>
                  <td><StatusBadge value={job.is_enabled} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <div className="grid-2">
        <section className="card">
          <h3>Recent Failed Runs</h3>
          {summary.recent_failed_runs.length === 0 ? <EmptyState text="No failed runs" /> : (
            <ul>
              {summary.recent_failed_runs.map((run) => (
                <li key={run.run_id}>
                  run #{run.run_id} | task #{run.task_id} ({run.task_name})
                  <div className="muted">{run.error_message ?? "-"}</div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card">
          <h3>Next Scheduled Runs</h3>
          {summary.next_scheduled_runs.length === 0 ? <EmptyState text="No upcoming runs" /> : (
            <ul>
              {summary.next_scheduled_runs.map((item) => (
                <li key={item.task_id}>
                  task #{item.task_id} ({item.task_name}) - {item.schedule_type}
                  <div className="muted">next: {item.next_run_at ?? "-"}</div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="card">
        <h3>Latest HTML Results</h3>
        {htmlResults.length === 0 ? <EmptyState text="No html results" /> : (
          <table className="table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Status</th>
                <th>Artifact</th>
                <th>Generated</th>
                <th>Preview</th>
              </tr>
            </thead>
            <tbody>
              {htmlResults.map((row) => (
                <tr key={row.task_id}>
                  <td>{row.task_name}</td>
                  <td><StatusBadge value={row.latest_run_status} /></td>
                  <td>{row.latest_artifact_id ?? "-"}</td>
                  <td>{row.latest_generated_at ?? "-"}</td>
                  <td>{row.preview_text ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default DashboardPage;
