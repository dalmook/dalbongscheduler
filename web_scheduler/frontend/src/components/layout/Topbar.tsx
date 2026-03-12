interface TopbarProps {
  healthStatus: string;
}

function Topbar({ healthStatus }: TopbarProps) {
  return (
    <header className="topbar">
      <div className="topbar-title">Scheduler Admin</div>
      <div className={`health-pill ${healthStatus === "ok" ? "ok" : "error"}`}>API: {healthStatus}</div>
    </header>
  );
}

export default Topbar;
