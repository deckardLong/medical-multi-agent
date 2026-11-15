import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MotionConfig } from "framer-motion";
import App from "./App";
import { ThemeProvider } from "./theme/ThemeProvider";
import { AuthProvider } from "./state/AuthContext";
import { ToastProvider } from "./state/ToastContext";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* reducedMotion="user": tôn trọng cài đặt "giảm chuyển động" của hệ điều hành */}
    <MotionConfig reducedMotion="user">
      <ThemeProvider>
        <ToastProvider>
          <BrowserRouter>
            <AuthProvider>
              <App />
            </AuthProvider>
          </BrowserRouter>
        </ToastProvider>
      </ThemeProvider>
    </MotionConfig>
  </StrictMode>,
);
