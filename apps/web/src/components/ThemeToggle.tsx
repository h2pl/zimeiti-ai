/** 主题切换——来源: Easel components/ThemeToggle.tsx（localStorage + dataset.theme）。 */
import { useEffect, useState } from "react";

function currentTheme(): "light" | "dark" {
  const t = document.documentElement.dataset.theme;
  return t === "dark" ? "dark" : "light";
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState(currentTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    try {
      localStorage.setItem("zimeiti_theme", theme);
    } catch { /* Storage may be unavailable. */ }
  }, [theme]);

  return (
    <button
      className="theme-toggle"
      title="切换明暗主题"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
