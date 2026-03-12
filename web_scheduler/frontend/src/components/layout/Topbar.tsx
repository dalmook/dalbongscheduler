interface Props {
  health: string;
}

function Topbar({ health }: Props) {
  return (
    <header className="topbar">
      <div className="top-title">web_scheduler admin</div>
      <div className={`health ${health === "ok" ? "ok" : "error"}`}>Health: {health}</div>
    </header>
  );
}

export default Topbar;
