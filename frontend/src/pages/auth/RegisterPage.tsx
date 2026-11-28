import { useMemo, useState, type FormEvent } from "react";
import { CalendarDays, CircleAlert, Lock, Mail, Phone, UserPlus } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Button, Input, Select } from "../../components/ui";
import { useAuth } from "../../state/AuthContext";
import { SocialLogin } from "../../components/SocialLogin";
import type { Gender } from "../../api/types";
import s from "./auth.module.css";

const today = new Date().toISOString().slice(0, 10);

function strength(pw: string): number {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) score++;
  return score;
}
const STRENGTH_COLOR = ["var(--c-danger)", "var(--c-danger)", "var(--c-warning)", "var(--c-accent)", "var(--c-success)"];

export default function RegisterPage() {
  const { register, loginSocial } = useAuth();
  const navigate = useNavigate();
  const [f, setF] = useState({ last_name: "", first_name: "", email: "", password: "", date_of_birth: "",
                               gender: "" as Gender | "", phone: "" });
  const [agree, setAgree] = useState(false);
  const [touched, setTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));

  const errors = useMemo(() => ({
    last_name: !f.last_name.trim() ? "Nhập họ" : null,
    first_name: !f.first_name.trim() ? "Nhập tên" : null,
    email: !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email.trim()) ? "Email không hợp lệ" : null,
    password: f.password.length < 8 ? "Tối thiểu 8 ký tự" : null,
    date_of_birth: f.date_of_birth && f.date_of_birth > today ? "Ngày sinh không thể ở tương lai" : null,
    phone: f.phone && !/^\+?[0-9 .-]{8,20}$/.test(f.phone.trim()) ? "Số điện thoại không hợp lệ" : null,
  }), [f]);
  const invalid = Object.values(errors).some(Boolean);
  const show = (k: keyof typeof errors) => (touched ? errors[k] : null);
  const pw = strength(f.password);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (invalid || !agree) return;
    setError(null);
    setBusy(true);
    try {
      await register({
        email: f.email.trim(), password: f.password, last_name: f.last_name.trim(), first_name: f.first_name.trim(),
        date_of_birth: f.date_of_birth || null, gender: f.gender || null, phone: f.phone.trim() || null,
      });
      navigate("/", { replace: true });
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className={s.title}>Bắt đầu ngay</h1>
      <p className={s.subtitle}>Tạo tài khoản cho cả gia đình trong một phút</p>
      <form className={s.form} onSubmit={onSubmit} noValidate>
        {error && <div className={s.formError} role="alert"><CircleAlert size={16} />{error}</div>}
        <div className={s.row}>
          <Input label="Họ" placeholder="Nguyễn Thị" autoComplete="family-name" autoFocus
                 value={f.last_name} onChange={set("last_name")} error={show("last_name")} />
          <Input label="Tên" placeholder="Lan" autoComplete="given-name"
                 value={f.first_name} onChange={set("first_name")} error={show("first_name")} />
        </div>
        <Input label="Email" type="email" icon={Mail} placeholder="ban@email.com" autoComplete="email"
               value={f.email} onChange={set("email")} error={show("email")} />
        <div className={s.field}>
          <Input label="Mật khẩu" type="password" icon={Lock} placeholder="Tối thiểu 8 ký tự" autoComplete="new-password"
                 value={f.password} onChange={set("password")} error={show("password")} />
          {f.password && (
            <div className={s.strength} aria-label={`Độ mạnh mật khẩu ${pw}/4`}>
              {[0, 1, 2, 3].map((i) => <span key={i} style={i < pw ? { background: STRENGTH_COLOR[pw] } : undefined} />)}
            </div>
          )}
        </div>
        <div className={s.row}>
          <Input label="Ngày sinh" type="date" icon={CalendarDays} max={today}
                 value={f.date_of_birth} onChange={set("date_of_birth")} error={show("date_of_birth")} />
          <Select label="Giới tính" value={f.gender} onChange={set("gender")}>
            <option value="">Không chọn</option>
            <option value="female">Nữ</option>
            <option value="male">Nam</option>
            <option value="other">Khác</option>
          </Select>
        </div>
        <Input label="Số điện thoại" labelAside={<span className="muted" style={{ fontWeight: 400 }}>Không bắt buộc</span>}
               type="tel" icon={Phone} placeholder="0912 345 678" autoComplete="tel"
               value={f.phone} onChange={set("phone")} error={show("phone")} />
        <label className={s.check}>
          <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
          <span>Tôi đồng ý với điều khoản sử dụng và chính sách dữ liệu sức khoẻ</span>
        </label>
        {touched && !agree && <span style={{ color: "var(--c-danger)", fontSize: 12, marginTop: -8 }}>Cần đồng ý điều khoản</span>}
        <Button type="submit" variant="primary" icon={UserPlus} loading={busy} block>Đăng ký</Button>
      </form>
      {/* Đăng ký bằng Google/Facebook: backend tự tạo tài khoản + gia đình nếu email chưa có */}
      <SocialLogin text="signup_with" disabled={busy} onToken={async (provider, token) => {
        await loginSocial(provider, token, true);
        navigate("/", { replace: true });
      }} />
      <p className={s.switch}>Đã có tài khoản?<Link to="/login">Đăng nhập</Link></p>
    </>
  );
}
