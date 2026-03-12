function StatusBadge({ value }: { value: string | boolean | null | undefined }) {
  const normalized = typeof value === "boolean" ? (value ? "enabled" : "disabled") : String(value ?? "unknown");
  return <span className={`status-badge ${normalized}`}>{normalized}</span>;
}

export default StatusBadge;
