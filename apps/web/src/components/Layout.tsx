import { NavLink, Outlet } from "react-router-dom";

const NAV = [
  { to: "/", label: "概览" },
  { to: "/approvals", label: "审批中心" },
  { to: "/ideas", label: "选题看板" },
  { to: "/calendar", label: "内容日历" },
  { to: "/profile", label: "画像管理" },
  { to: "/trends", label: "趋势" },
  { to: "/outputs", label: "内容库" },
  { to: "/logs", label: "执行日志" },
];

/** 侧边栏布局（对标 Easel web App 路由形态）。 */
export default function Layout() {
  return (
    <div className="shell">
      <nav className="sidebar">
        <div className="brand">Zimeiti AI</div>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
          >
            {n.label}
          </NavLink>
        ))}
      </nav>
      <main className="container">
        <Outlet />
      </main>
    </div>
  );
}
