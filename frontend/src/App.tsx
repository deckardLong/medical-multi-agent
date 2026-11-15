import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import AuthLayout from "./pages/auth/AuthLayout";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import { CalendarPage, ChatPage, DashboardPage, RecordsPage } from "./pages/lazy";
import { useAuth } from "./state/AuthContext";

export default function App() {
  const { ready } = useAuth();
  if (!ready) return null;          // đang kiểm tra token cũ: không render gì để tránh nháy trang đăng nhập

  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/records" element={<RecordsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
