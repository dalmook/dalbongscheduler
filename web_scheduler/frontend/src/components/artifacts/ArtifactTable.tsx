import { API_BASE_URL } from "../../api/client";
import type { Artifact } from "../../types/artifact";

function ArtifactTable({ rows, onPreview }: { rows: Artifact[]; onPreview: (artifact: Artifact) => void }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>작업</th>
          <th>실행</th>
          <th>유형</th>
          <th>버전</th>
          <th>최신</th>
          <th>생성시각</th>
          <th>동작</th>
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
            <td className="row">
              <button className="btn" onClick={() => onPreview(a)}>미리보기</button>
              <a className="btn" href={`${API_BASE_URL}/artifacts/${a.id}/download.xlsx`} target="_blank" rel="noreferrer">엑셀</a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default ArtifactTable;
