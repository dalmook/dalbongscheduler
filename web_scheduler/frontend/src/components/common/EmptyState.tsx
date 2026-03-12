function EmptyState({ text = "No data" }: { text?: string }) {
  return <div className="state">{text}</div>;
}

export default EmptyState;
