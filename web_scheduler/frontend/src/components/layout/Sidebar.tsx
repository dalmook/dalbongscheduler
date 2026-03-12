import { NavLink } from "react-router-dom";

const menus = [
  { to: "/", label: "Dashboard" },
  { to: "/tasks", label: "Tasks" },
  { to: "/runs", label: "Runs" },
  { to: "/html-results", label: "HTML Results" },
];

function Sidebar() {
  return (
    <aside className="sidebar">
      <h2>web_scheduler</h2>
      <nav>
        {menus.map((menu) => (
          <NavLink key={menu.to} to={menu.to} end={menu.to === "/"} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            {menu.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

export default Sidebar;
