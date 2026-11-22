import { createContext, useCallback, useContext, useLayoutEffect, useMemo, useState, type ReactNode } from "react";
import { flushSync } from "react-dom";
import { globalVars, themeFactories, type ThemeName, type UIThemeFactory } from "./factory";

// Khoá mới: bản cũ ("fh.theme") ghi theme ở MỌI lần tải trang nên không phân biệt được người dùng đã tự chọn hay chưa
const STORAGE_KEY = "aurelia.theme";

interface ThemeCtx {
  name: ThemeName;
  factory: UIThemeFactory;
  toggle: (origin?: { x: number; y: number }) => void;
}

const Ctx = createContext<ThemeCtx | null>(null);

function initialTheme(): ThemeName {
  const t = document.documentElement.dataset.theme;          // đã đặt sẵn bởi script trong index.html
  return t === "dark" ? "dark" : "light";             // mặc định Light
}

type ViewTransitionDoc = Document & { startViewTransition?: (cb: () => void) => { ready: Promise<void> } };

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [name, setName] = useState<ThemeName>(initialTheme);
  const factory = themeFactories[name];

  useLayoutEffect(() => {
    const root = document.documentElement;
    for (const [k, v] of Object.entries(globalVars(factory))) root.style.setProperty(k, v);
    root.dataset.theme = name;
  }, [factory, name]);

  const toggle = useCallback((origin?: { x: number; y: number }) => {
    const next: ThemeName = name === "dark" ? "light" : "dark";
    // Chỉ lưu khi người dùng tự đổi → chưa từng đổi thì luôn theo mặc định (Light)
    try { localStorage.setItem(STORAGE_KEY, next); localStorage.removeItem("fh.theme"); } catch { /* chế độ riêng tư */ }
    const doc = document as ViewTransitionDoc;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!doc.startViewTransition || reduce) {
      setName(next);
      return;
    }
    // View Transitions: trình duyệt chụp ảnh trước/sau rồi tự chuyển cảnh trên GPU — mượt hơn nhiều so với cho
    // hàng trăm phần tử cùng chạy CSS transition màu (nguyên nhân giật khi đổi theme)
    const x = origin?.x ?? innerWidth - 40, y = origin?.y ?? 40;
    const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    const vt = doc.startViewTransition(() => flushSync(() => setName(next)));
    vt.ready.then(() => {
      document.documentElement.animate(
        { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${r}px at ${x}px ${y}px)`] },
        { duration: 520, easing: "cubic-bezier(0.22, 1, 0.36, 1)", pseudoElement: "::view-transition-new(root)" },
      );
    }).catch(() => undefined);
  }, [name]);

  const value = useMemo(() => ({ name, factory, toggle }), [name, factory, toggle]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTheme phải nằm trong <ThemeProvider>");
  return ctx;
}

/** Component chỉ biết tới interface factory — không biết đang là theme nào. */
export function useUI(): UIThemeFactory {
  return useTheme().factory;
}
