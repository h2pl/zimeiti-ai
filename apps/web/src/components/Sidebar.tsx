/** 侧边栏——参考: Easel components/Sidebar.tsx 模式（导航+状态点+主题切换）。 */
import type { Page } from "../App";
import { IconCalendar, IconCheck, IconDashboard, IconFolder, IconIdea, IconList, IconTrend, IconUser } from "./icons";

const NAV: { page: Page; label: string; icon: typeof IconDashboard }[] = [
  { page: "dashboard", label: "概览", icon: IconDashboard },
  { page: "approvals", label: "审批中心", icon: IconCheck },
  { page: "ideas", label: "选题看板", icon: IconIdea },
  { page: "calendar", label: "内容日历", icon: IconCalendar },
  { page: "profile", label: "画像管理", icon: IconUser },
  { page: "trends", label: "趋势", icon: IconTrend },
  { page: "outputs", label: "内容库", icon: IconFolder },
  { page: "logs", label: "执行日志", icon: IconList },
];

export default function Sidebar({
  currentPage,
  onPageChange,
  accountStatus,
}: {
  currentPage: Page;
  onPageChange: (p: Page) => void;
  accountStatus: Record<string, boolean>;
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <h1>Zimeiti AI</h1>
        </div>
      </div>
      <div className="sidebar-section">
        {NAV.map((n) => (
          <button
            key={n.page}
            className={currentPage === n.page ? "nav-item active" : "nav-item"}
            onClick={() => onPageChange(n.page)}
          >
            <span className="nav-icon">
              <n.icon size={17} />
            </span>
            {n.label}
          </button>
        ))}
      </div>
      <div className="sidebar-footer">
        {Object.entries(accountStatus).map(([account, enabled]) => (
          <div key={account} className="status-row">
            <span className={enabled ? "status-dot online" : "status-dot offline"} />
            <span className="status-row-text">
              {account} {enabled ? "" : "（停用）"}
            </span>
          </div>
        ))}
      </div>
    </aside>
  );
}
