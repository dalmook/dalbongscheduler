import type { ArtifactListItem } from "../../types/artifact";

interface Props {
  artifacts: ArtifactListItem[];
  onPreview: (artifactId: number) => void;
}

function ArtifactTable({ artifacts, onPreview }: Props) {
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
          <th></th>
        </tr>
      </thead>
      <tbody>
        {artifacts.map((artifact) => (
          <tr key={artifact.id}>
            <td>{artifact.id}</td>
            <td>{artifact.task_id}</td>
            <td>{artifact.run_id}</td>
            <td>{artifact.artifact_type}</td>
            <td>{artifact.version_no}</td>
            <td>{String(artifact.is_latest)}</td>
            <td>{artifact.created_at}</td>
            <td>{artifact.artifact_type === "html" && <button className="btn" onClick={() => onPreview(artifact.id)}>Preview</button>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default ArtifactTable;
