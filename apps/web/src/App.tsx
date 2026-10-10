/**
 * 顶层组装器——参考: Easel App.tsx（useState<Page> + switch 渲染，无路由库）。
 * 刷新保持当前页（sessionStorage，体验增强；Easel 无此需求）。
 */
import { useEffect, useState } from "react";
import AccountsPage from "./components/AccountsPage";
import ApprovalsPage from "./components/ApprovalsPage";
import ChatPage from "./components/ChatPage";
import PublishCenterPage from "./components/PublishCenterPage";
import BreakdownPage from "./components/BreakdownPage";
import SettingsPage from "./components/SettingsPage";
import SkillPage from "./components/SkillPage";
import CalendarPage from "./components/CalendarPage";
import DashboardPage from "./components/DashboardPage";
import IdeasPage from "./components/IdeasPage";
import LogsPage from "./components/LogsPage";
import OutputsPage from "./components/OutputsPage";
import ProfilePage from "./components/ProfilePage";
import Sidebar from "./components/Sidebar";
import TrendsPage from "./components/TrendsPage";
import { fetchProfiles } from "./lib/api";

export type Page =
  | "chat"
  | "publish"
  | "dashboard"
  | "approvals"
  | "accounts"
  | "breakdown"
  | "skills"
  | "settings"
  | "ideas"
  | "calendar"
  | "profile"
  | "trends"
  | "outputs"
  | "logs";

const PAGES: Page[] = [
  "chat",
  "publish",
  "dashboard",
  "approvals",
  "accounts",
  "breakdown",
  "skills",
  "settings",
  "ideas",
  "calendar",
  "profile",
  "trends",
  "outputs",
  "logs",
];

function loadPage(): Page {
  try {
    const saved = sessionStorage.getItem("zimeiti_page") as Page | null;
    if (saved && PAGES.includes(saved)) return saved;
  } catch { /* Storage may be unavailable. */ }
  return "dashboard";
}

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>(loadPage);
  const [accountStatus, setAccountStatus] = useState<Record<string, boolean>>({});

  useEffect(() => {
    try {
      sessionStorage.setItem("zimeiti_page", currentPage);
    } catch { /* Storage may be unavailable. */ }
  }, [currentPage]);

  useEffect(() => {
    // D5：侧边栏账号状态点（复核 fetchProfiles 数据源）
    const load = () =>
      fetchProfiles()
        .then((list) =>
          setAccountStatus(Object.fromEntries(list.map((a) => [a.account, a.enabled]))),
        )
        .catch(() => {});
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  function renderPage() {
    switch (currentPage) {
      case "approvals":
        return <ApprovalsPage />;
      case "ideas":
        return <IdeasPage />;
      case "calendar":
        return <CalendarPage />;
      case "profile":
        return <ProfilePage />;
      case "trends":
        return <TrendsPage />;
      case "outputs":
        return <OutputsPage />;
      case "accounts":
        return <AccountsPage />;
      case "breakdown":
        return <BreakdownPage />;
      case "skills":
        return <SkillPage />;
      case "settings":
        return <SettingsPage />;
      case "chat":
        return <ChatPage />;
      case "publish":
        return <PublishCenterPage />;
      case "logs":
        return <LogsPage />;
      default:
        return <DashboardPage onNavigate={setCurrentPage} />;
    }
  }

  return (
    <div className="app-layout">
      <Sidebar currentPage={currentPage} onPageChange={setCurrentPage} accountStatus={accountStatus} />
      <main className="main-content">
        <div className="page-host">{renderPage()}</div>
      </main>
    </div>
  );
}
