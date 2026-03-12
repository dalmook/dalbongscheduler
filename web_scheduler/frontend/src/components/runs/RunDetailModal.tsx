import type { Run } from "../../types/run";

function RunDetailModal({ run, onClose }: { run: Run | null; onClose: () => void }) {
  if (!run) return null;

  return (
    <div className="modal-overlay">
      <div className="modal small">
        <h3>Run #{run.id}</h3>
        <p><b>status:</b> {run.status}</p>
        <p><b>result_summary:</b> {run.result_summary ?? "-"}</p>
        <p><b>error_message:</b> {run.error_message ?? "-"}</p>
        <div className="row right">
          <button className="btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default RunDetailModal;
