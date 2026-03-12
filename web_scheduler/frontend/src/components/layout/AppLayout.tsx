import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { useEffect, useState } from "react";
import { getHealth } from "../../api/health";

function AppLayout() {
  const [health, setHealth] = useState("checking");

  useEffect(() => {
    getHealth()
      .then((res) => setHealth(res.status))
      .catch(() => setHealth("error"));
  }, []);

  return (
    <div className="layout">
      <Sidebar />
      <div className="main-wrap">
        <Topbar health={health} />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AppLayout;
