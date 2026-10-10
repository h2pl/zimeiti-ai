import { Route, Routes } from "react-router-dom";
import "./App.css";
import Layout from "./components/Layout";
import Approvals from "./pages/Approvals";
import CalendarPage from "./pages/CalendarPage";
import Dashboard from "./pages/Dashboard";
import Ideas from "./pages/Ideas";
import Logs from "./pages/Logs";
import Outputs from "./pages/Outputs";
import Profile from "./pages/Profile";
import TrendsPage from "./pages/Trends";

/** 路由化工作台（web-workbench：Layout 侧边栏 + 8 页面）。 */
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/ideas" element={<Ideas />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/trends" element={<TrendsPage />} />
        <Route path="/outputs" element={<Outputs />} />
        <Route path="/logs" element={<Logs />} />
      </Route>
    </Routes>
  );
}
