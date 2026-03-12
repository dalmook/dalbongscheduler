import { Link } from "react-router-dom";
import type { Task } from "../../types/task";
import StatusBadge from "../common/StatusBadge";

interface Props {
  rows: Task[];
  onRun: (task: Task) => void;
  onEdit: (task: Task) => void;
  onDelete: (task: Task) => void;
}

function TaskTable({ rows, onRun, onEdit, onDelete }: Props) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Type</th>
          <th>Schedule</th>
          <th>Enabled</th>
          <th>Timezone</th>
          <th>Next Run</th>
          <th>Last Run</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((task) => (
          <tr key={task.id}>
            <td>{task.id}</td>
            <td>{task.name}</td>
            <td>{task.task_type}</td>
            <td>{task.schedule_type}</td>
            <td><StatusBadge value={task.is_enabled} /></td>
            <td>{task.timezone ?? "-"}</td>
            <td>{task.next_run_at ?? "-"}</td>
            <td>
              <StatusBadge value={task.last_run_status} />
              <div className="muted">{task.last_run_at ?? "-"}</div>
            </td>
            <td className="row">
              <Link className="btn" to={`/tasks/${task.id}`}>Detail</Link>
              <button className="btn" onClick={() => onRun(task)}>Run</button>
              <button className="btn" onClick={() => onEdit(task)}>Edit</button>
              <button className="btn danger" onClick={() => onDelete(task)}>Delete</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default TaskTable;
