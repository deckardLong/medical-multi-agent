import { Suspense, useEffect } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  CalendarDays, Check, ChevronDown, ClipboardList, LayoutDashboard, LogOut, Moon, Sparkles, Sun, Users,
} from "lucide-react";
import { AureliaMark } from "../AureliaMark";
import { Link, NavLink, Navigate, useLocation, useOutlet } from "react-router-dom";
import { Avatar, Skeleton } from "../ui";
import { AvatarUploader } from "../AvatarUploader";
import { LinkedAccounts } from "../LinkedAccounts";
import { Popover } from "./Popover";
import { useAuth } from "../../state/AuthContext";
import { MemberProvider, useMembers } from "../../state/MemberContext";
import { useTheme } from "../../theme/ThemeProvider";
import { MEMBER_TYPE } from "../../lib/format";
import { prefetchPages } from "../../pages/lazy";
import s from "./shell.module.css";

const NAV = [
  { to: "/", label: "Tổng quan", icon: LayoutDashboard },
  { to: "/chat", label: "AURELIA", icon: Sparkles },
  { to: "/calendar", label: "Lịch", icon: CalendarDays },
  { to: "/records", label: "Hồ sơ", icon: ClipboardList },
];

function MemberSwitcher() {
  const { members, current, select } = useMembers();
  if (!current) return null;
  return (
    <Popover trigger={(open, toggle) => (
      <button className={s.navBtn} onClick={toggle} aria-expanded={open} aria-label="Chọn thành viên đang xem">
        <Users size={16} />
        <span style={{ fontSize: 13 }}>{current.display_name}</span>
        <ChevronDown size={14} style={{ transition: "transform 200ms", transform: open ? "rotate(180deg)" : "none" }} />
      </button>
    )}>
      {(close) => (
        <>
          <div className="muted" style={{ fontSize: 12, padding: "6px 10px" }}>Đang xem dữ liệu của</div>
          {members.map((m) => (
            <button key={m.id} role="menuitemradio" aria-checked={m.id === current.id}
                    className={`${s.popItem} ${m.id === current.id ? s.popItemActive : ""}`}
                    onClick={() => { select(m.id); close(); }}>
              <Avatar name={m.display_name} size={32} memberId={m.id} version={m.avatar_updated_at} />
              <span style={{ flex: 1 }}>{m.display_name}<small>{MEMBER_TYPE[m.member_type]}</small></span>
              {m.id === current.id && <Check size={16} color="var(--c-accent)" />}
            </button>
          ))}
        </>
      )}
    </Popover>
  );
}

function AccountMenu() {
  const { user, logout } = useAuth();
  const { family, members, reload } = useMembers();
  if (!user) return null;
  // Avatar của tài khoản = avatar của thành viên "bản thân" (liên kết với chính tài khoản này)
  const me = members.find((m) => m.linked_user_id === user.id) ?? members.find((m) => m.member_type === "self");
  return (
    <Popover trigger={(open, toggle) => (
      <button className={s.account} onClick={toggle} aria-expanded={open} aria-label="Tài khoản">
        <span><strong>{family?.name ?? user.display_name}</strong><small>{user.email}</small></span>
        <Avatar name={user.display_name} size={32} memberId={me?.id} version={me?.avatar_updated_at} />
      </button>
    )}>
      {() => (
        <>
          <div style={{ padding: "10px 10px 8px", display: "flex", alignItems: "center", gap: 14 }}>
            {me && <AvatarUploader memberId={me.id} name={user.display_name} version={me.avatar_updated_at} size={52}
                                   onChanged={reload} />}
            <div>
              <strong>{user.display_name}</strong>
              <div className="muted" style={{ fontSize: 13 }}>{user.email}</div>
            </div>
          </div>
          <div className={s.popDivider} />
          <LinkedAccounts />
          <div className={s.popDivider} />
          <button className={s.popItem} onClick={logout}><LogOut size={16} />Đăng xuất</button>
        </>
      )}
    </Popover>
  );
}

function PageArea() {
  const location = useLocation();
  const outlet = useOutlet();
  const reduce = useReducedMotion();
  const offset = reduce ? 0 : 10;
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div key={location.pathname} className={s.page}
                  initial={{ opacity: 0, y: offset }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -offset / 2 }}
                  transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}>
        <Suspense fallback={<div style={{ display: "grid", gap: 14 }}><Skeleton h={34} w={260} /><Skeleton h={180} /></div>}>
          {outlet}
        </Suspense>
      </motion.div>
    </AnimatePresence>
  );
}

export default function AppShell() {
  const { user, ready } = useAuth();
  const { name, toggle } = useTheme();
  const location = useLocation();

  useEffect(() => {
    if (!user) return;
    // Tải trước code các trang khi trình duyệt rảnh → lần đầu bấm chuyển trang không phải chờ tải chunk
    const w = window as Window & { requestIdleCallback?: (cb: () => void) => number; cancelIdleCallback?: (id: number) => void };
    if (w.requestIdleCallback && w.cancelIdleCallback) {
      const id = w.requestIdleCallback(prefetchPages);
      return () => w.cancelIdleCallback!(id);
    }
    const id = window.setTimeout(prefetchPages, 1200);
    return () => clearTimeout(id);
  }, [user]);

  if (!ready) return null;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <MemberProvider>
      <div className={s.app}>
        <div className={s.frame}>
          <header className={s.nav}>
            <Link to="/" className={s.logo} aria-label="AURELIA — về trang tổng quan">
              <span className={s.logoMark}><AureliaMark size={26} /></span>
              <span className="gradient-text">AURELIA</span>
            </Link>
            <nav className={s.links} aria-label="Điều hướng chính">
              {NAV.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `${s.link} ${isActive ? s.linkActive : ""}`}>
                  {({ isActive }) => (
                    <>
                      <Icon size={16} />
                      <span className={s.linkLabel}>{label}</span>
                      {isActive && <motion.span layoutId="nav-underline" className={s.underline}
                                                transition={{ type: "spring", stiffness: 520, damping: 40 }} />}
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
            <div className={s.spacer} />
            <MemberSwitcher />
            <button className={s.navBtn} onClick={(e) => toggle({ x: e.clientX, y: e.clientY })}
                    aria-label={name === "dark" ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}>
              {name === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <AccountMenu />
          </header>
          <main className={s.content}>
            <PageArea />
          </main>
        </div>
      </div>
    </MemberProvider>
  );
}
