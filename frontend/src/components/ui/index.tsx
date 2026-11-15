import {
  forwardRef, useEffect, useId, useState, type ButtonHTMLAttributes, type CSSProperties, type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes, type TextareaHTMLAttributes,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Eye, EyeOff, Inbox, X, type LucideIcon } from "lucide-react";
import { useUI } from "../../theme/ThemeProvider";
import type { BadgeTone, ButtonVariant, CardTone } from "../../theme/factory";
import { initials } from "../../lib/format";
import s from "./ui.module.css";

const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

/* ---------- Button ---------- */
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "md" | "sm";
  icon?: LucideIcon;
  loading?: boolean;
  block?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", icon: Icon, loading, block, children, className, disabled, style, ...rest }, ref,
) {
  const skin = useUI().createButtonSkin(variant);
  const iconOnly = !children && !!Icon;
  return (
    <button ref={ref} className={cx(s.btn, size === "sm" && s.sm, block && s.block, iconOnly && s.iconOnly, className)}
            style={{ ...skin, ...style }} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? <span className={s.spinner} aria-hidden /> : Icon && <Icon size={size === "sm" ? 15 : 17} aria-hidden />}
      {children}
    </button>
  );
});

/* ---------- Card ---------- */
export function Card({ tone = "default", title, action, className, children }: {
  tone?: CardTone; title?: ReactNode; action?: ReactNode; className?: string; children?: ReactNode;
}) {
  const skin = useUI().createCardSkin(tone);
  return (
    <section className={cx(s.card, className)} style={skin}>
      {(title || action) && (
        <div className={s.cardTitle}>
          {typeof title === "string" ? <h3>{title}</h3> : title}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

/* ---------- Field (label + input/select/textarea) ---------- */
interface FieldShell {
  label?: ReactNode;
  labelAside?: ReactNode;
  hint?: ReactNode;
  error?: string | null;
  icon?: LucideIcon;
}

function Shell({ id, label, labelAside, hint, error, children }: FieldShell & { id: string; children: ReactNode }) {
  return (
    <div className={s.field}>
      {label && (
        <label className={s.label} htmlFor={id}>
          <span>{label}</span>
          {labelAside}
        </label>
      )}
      {children}
      {error ? <span className={s.error} id={`${id}-err`} role="alert">{error}</span>
        : hint && <span className={s.hint}>{hint}</span>}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & FieldShell>(function Input(
  { label, labelAside, hint, error, icon: Icon, type, className, ...rest }, ref,
) {
  const skin = useUI().createInputSkin();
  const id = useId();
  const [show, setShow] = useState(false);
  const isPassword = type === "password";
  return (
    <Shell id={id} label={label} labelAside={labelAside} hint={hint} error={error}>
      <div className={s.control} style={skin}>
        {Icon && <Icon size={16} aria-hidden />}
        <input ref={ref} id={id} type={isPassword && show ? "text" : type} aria-invalid={!!error || undefined}
               aria-describedby={error ? `${id}-err` : undefined}
               className={cx(s.input, Icon && s.withIcon, isPassword && s.withAction, className)} {...rest} />
        {isPassword && (
          <button type="button" className={s.inputAction} onClick={() => setShow((v) => !v)}
                  aria-label={show ? "Ẩn mật khẩu" : "Hiện mật khẩu"}>
            {show ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        )}
      </div>
    </Shell>
  );
});

export function Select({ label, hint, error, children, className, ...rest }:
  SelectHTMLAttributes<HTMLSelectElement> & FieldShell) {
  const skin = useUI().createInputSkin();
  const id = useId();
  return (
    <Shell id={id} label={label} hint={hint} error={error}>
      <div className={s.control} style={skin}>
        <select id={id} className={cx(s.input, className)} aria-invalid={!!error || undefined} {...rest}>{children}</select>
      </div>
    </Shell>
  );
}

export function TextArea({ label, hint, error, className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement> & FieldShell) {
  const skin = useUI().createInputSkin();
  const id = useId();
  return (
    <Shell id={id} label={label} hint={hint} error={error}>
      <div className={s.control} style={skin}>
        <textarea id={id} className={cx(s.input, className)} {...rest} />
      </div>
    </Shell>
  );
}

/* ---------- Nút xoá 2 bước: bấm lần 1 đổi thành "Chắc chắn?", 3 giây không bấm thì trở lại ---------- */
export function ConfirmButton({ onConfirm, children = "Xoá", confirmText = "Chắc chắn?", icon, loading }: {
  onConfirm: () => void; children?: ReactNode; confirmText?: string; icon?: LucideIcon; loading?: boolean;
}) {
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    if (!armed) return;
    const t = setTimeout(() => setArmed(false), 3000);
    return () => clearTimeout(t);
  }, [armed]);
  return (
    <Button size="sm" variant={armed ? "danger" : "ghost"} icon={icon} loading={loading}
            onClick={() => (armed ? (setArmed(false), onConfirm()) : setArmed(true))}>
      {armed ? confirmText : children}
    </Button>
  );
}

/* ---------- Badge / Avatar ---------- */
export function Badge({ tone = "neutral", icon: Icon, children }: { tone?: BadgeTone; icon?: LucideIcon; children: ReactNode }) {
  const skin = useUI().createBadgeSkin(tone);
  return <span className={s.badge} style={skin}>{Icon && <Icon size={12} aria-hidden />}{children}</span>;
}

export function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  return (
    <span className={s.avatar} style={{ width: size, height: size, fontSize: size * 0.36, borderRadius: size * 0.34 }}
          aria-hidden>
      {initials(name)}
    </span>
  );
}

/* ---------- Tabs: thanh trượt dùng layoutId → framer-motion tự nội suy vị trí (transform), không reflow ---------- */
export function Tabs<T extends string>({ value, onChange, items, id }: {
  value: T; onChange: (v: T) => void; items: { value: T; label: ReactNode }[]; id: string;
}) {
  return (
    <div className={s.tabs} role="tablist">
      {items.map((it) => (
        <button key={it.value} role="tab" aria-selected={value === it.value}
                className={cx(s.tab, value === it.value && s.tabActive)} onClick={() => onChange(it.value)}>
          {value === it.value && (
            <motion.span layoutId={`tab-pill-${id}`} className={s.tabPill} transition={{ type: "spring", stiffness: 500, damping: 38 }} />
          )}
          {it.label}
        </button>
      ))}
    </div>
  );
}

/* ---------- Empty / Skeleton ---------- */
export function Empty({ icon: Icon = Inbox, title, children }: { icon?: LucideIcon; title: string; children?: ReactNode }) {
  return (
    <div className={s.empty}>
      <Icon size={28} aria-hidden />
      <strong style={{ color: "var(--c-text)" }}>{title}</strong>
      {children && <span style={{ fontSize: 13 }}>{children}</span>}
    </div>
  );
}

export function Skeleton({ h = 16, w = "100%", style }: { h?: number; w?: number | string; style?: CSSProperties }) {
  return <div className={s.skeleton} style={{ height: h, width: w, ...style }} aria-hidden />;
}

/* ---------- Modal ---------- */
export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div className={s.overlay} onMouseDown={(e) => e.target === e.currentTarget && onClose()}
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.18 }}>
          <motion.div className={s.modal} role="dialog" aria-modal="true" aria-label={title}
                      initial={{ opacity: 0, y: 14, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 8, scale: 0.98 }} transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}>
            <div className={s.modalHead}>
              <h3>{title}</h3>
              <Button variant="ghost" size="sm" icon={X} onClick={onClose} aria-label="Đóng" />
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export { s as uiStyles, cx };
