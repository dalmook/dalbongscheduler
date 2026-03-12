function Loading({ text = "Loading..." }: { text?: string }) {
  return <div className="state-box">{text}</div>;
}

export default Loading;
