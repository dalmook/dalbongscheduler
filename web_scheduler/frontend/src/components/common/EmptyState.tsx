function EmptyState({ message = "No data" }: { message?: string }) {
  return <div className="state-box">{message}</div>;
}

export default EmptyState;
