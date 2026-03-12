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
          <th>이름</th>
          <th>유형</th>
          <th>스케줄</th>
          <th>사용</th>
          <th>시간대</th>
          <th>다음 실행</th>
          <th>최근 실행</th>
          <th>작업</th>
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
              <Link className="btn" to={`/tasks/${task.id}`}>상세</Link>
              <button className="btn" onClick={() => onRun(task)}>실행</button>
              <button className="btn" onClick={() => onEdit(task)}>수정</button>
              <button className="btn danger" onClick={() => onDelete(task)}>삭제</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default TaskTable;
