function StatusBadge({ value }: { value: string | boolean | null | undefined }) {
  const label = typeof value === "boolean" ? (value ? "enabled" : "disabled") : String(value ?? "unknown");
  return <span className={`badge ${label}`}>{label}</span>;
}

export default StatusBadge;
