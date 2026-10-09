import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // 开发期代理到 FastAPI（生产由反向代理承担）
      "/api": "http://localhost:8000",
    },
  },
});
