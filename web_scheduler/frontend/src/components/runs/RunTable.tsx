import type { Run } from "../../types/run";
import StatusBadge from "../common/StatusBadge";

function RunTable({ rows, onDetail }: { rows: Run[]; onDetail: (run: Run) => void }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Run ID</th>
          <th>Task ID</th>
          <th>Trigger</th>
          <th>Status</th>
          <th>Started</th>
          <th>Finished</th>
          <th>Duration</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((run) => (
          <tr key={run.id}>
            <td>{run.id}</td>
            <td>{run.task_id}</td>
            <td>{run.trigger_type}</td>
            <td><StatusBadge value={run.status} /></td>
            <td>{run.started_at ?? "-"}</td>
            <td>{run.finished_at ?? "-"}</td>
            <td>{run.duration_ms ?? "-"}</td>
            <td><button className="btn" onClick={() => onDetail(run)}>Detail</button></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default RunTable;
