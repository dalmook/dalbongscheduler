import type { Artifact } from "../../types/artifact";

function ArtifactTable({ rows, onPreview }: { rows: Artifact[]; onPreview: (artifact: Artifact) => void }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Task</th>
          <th>Run</th>
          <th>Type</th>
          <th>Version</th>
          <th>Latest</th>
          <th>Created</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((a) => (
          <tr key={a.id}>
            <td>{a.id}</td>
            <td>{a.task_id}</td>
            <td>{a.run_id}</td>
            <td>{a.artifact_type}</td>
            <td>{a.version_no}</td>
            <td>{String(a.is_latest)}</td>
            <td>{a.created_at}</td>
            <td><button className="btn" onClick={() => onPreview(a)}>Preview</button></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default ArtifactTable;
