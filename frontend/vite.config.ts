import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import basicSsl from "@vitejs/plugin-basic-ssl";

// /api/* được proxy sang FastAPI (cổng 8000) → frontend và backend cùng origin, không cần cấu hình CORS khi dev
// `npm run dev:https` (mode "https"): HTTPS với chứng chỉ tự ký — Facebook chặn đăng nhập trên trang http, kể cả localhost
export default defineConfig(({ mode }) => ({
  plugins: mode === "https" ? [react(), basicSsl()] : [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: {
    target: "es2020",
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          motion: ["framer-motion"],
        },
      },
    },
  },
}));
