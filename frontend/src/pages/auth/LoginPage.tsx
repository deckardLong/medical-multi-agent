import { useState, type FormEvent } from "react";
import { CircleAlert, Lock, LogIn, Mail } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button, Input } from "../../components/ui";
import { useAuth } from "../../state/AuthContext";
import s from "./auth.module.css";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password, remember);
      navigate(from, { replace: true });
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className={s.title}>Chào mừng trở lại!</h1>
      <p className={s.subtitle}>Nhập thông tin để truy cập tài khoản của bạn</p>
      <form className={s.form} onSubmit={onSubmit} noValidate>
        {error && <div className={s.formError} role="alert"><CircleAlert size={16} />{error}</div>}
        <Input label="Email" type="email" icon={Mail} placeholder="ban@email.com" autoComplete="email" autoFocus
               value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Input label="Mật khẩu" type="password" icon={Lock} placeholder="Nhập mật khẩu" autoComplete="current-password"
               value={password} onChange={(e) => setPassword(e.target.value)} required />
        <label className={s.check}>
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
          Ghi nhớ đăng nhập trên thiết bị này
        </label>
        <Button type="submit" variant="primary" icon={LogIn} loading={busy} block disabled={!email || !password}>
          Đăng nhập
        </Button>
      </form>
      <p className={s.switch}>Chưa có tài khoản?<Link to="/register">Đăng ký</Link></p>
    </>
  );
}
