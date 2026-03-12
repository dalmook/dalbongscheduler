interface Props {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmDialog({ open, title, message, onConfirm, onCancel }: Props) {
  if (!open) return null;
  return (
    <div className="modal-overlay">
      <div className="modal small">
        <h3>{title}</h3>
        <p>{message}</p>
        <div className="row right">
          <button className="btn" onClick={onCancel}>Cancel</button>
          <button className="btn danger" onClick={onConfirm}>Delete</button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;
