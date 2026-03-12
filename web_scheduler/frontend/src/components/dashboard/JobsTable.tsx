import type { DashboardJob } from "../../types/dashboard";

function JobsTable({ jobs }: { jobs: DashboardJob[] }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Job ID</th>
          <th>Task ID</th>
          <th>Name</th>
          <th>Trigger</th>
          <th>Next Run</th>
          <th>Enabled</th>
        </tr>
      </thead>
      <tbody>
        {jobs.map((job) => (
          <tr key={job.job_id}>
            <td>{job.job_id}</td>
            <td>{job.task_id ?? "-"}</td>
            <td>{job.task_name ?? "-"}</td>
            <td>{job.trigger}</td>
            <td>{job.next_run_time ?? "-"}</td>
            <td>{String(job.is_enabled)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default JobsTable;
