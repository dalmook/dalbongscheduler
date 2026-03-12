import type { Run } from "../../types/run";
import StatusBadge from "../common/StatusBadge";

interface Props {
  runs: Run[];
  onSelect: (run: Run) => void;
}

function RunTable({ runs, onSelect }: Props) {
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
          <th>Duration(ms)</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr key={run.id}>
            <td>{run.id}</td>
            <td>{run.task_id}</td>
            <td>{run.trigger_type}</td>
            <td><StatusBadge value={run.status} /></td>
            <td>{run.started_at ?? "-"}</td>
            <td>{run.finished_at ?? "-"}</td>
            <td>{run.duration_ms ?? "-"}</td>
            <td><button className="btn" onClick={() => onSelect(run)}>View</button></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default RunTable;
