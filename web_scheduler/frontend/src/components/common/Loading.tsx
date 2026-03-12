function Loading({ text = "Loading..." }: { text?: string }) {
  return <div className="state">{text}</div>;
}

export default Loading;
