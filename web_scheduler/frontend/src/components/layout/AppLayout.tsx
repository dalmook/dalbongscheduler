import { Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { healthCheck } from "../../api/client";

function AppLayout() {
  const [healthStatus, setHealthStatus] = useState("checking");

  useEffect(() => {
    healthCheck()
      .then((res) => setHealthStatus(res.status))
      .catch(() => setHealthStatus("error"));
  }, []);

  return (
    <div className="layout">
      <Sidebar />
      <div className="content-wrap">
        <Topbar healthStatus={healthStatus} />
        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AppLayout;
