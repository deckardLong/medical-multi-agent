import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CircleAlert, CircleCheck } from "lucide-react";
import { uiStyles as s, cx } from "../components/ui";

interface Toast { id: number; kind: "success" | "error"; text: string }
interface ToastCtx { success: (text: string) => void; error: (text: string) => void }

const Ctx = createContext<ToastCtx | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const seq = useRef(0);

  const push = useCallback((kind: Toast["kind"], text: string) => {
    const id = ++seq.current;
    setItems((xs) => [...xs.slice(-3), { id, kind, text }]);
    setTimeout(() => setItems((xs) => xs.filter((t) => t.id !== id)), kind === "error" ? 6000 : 3500);
  }, []);

  const value = useMemo(() => ({ success: (t: string) => push("success", t), error: (t: string) => push("error", t) }), [push]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <div className={s.toasts} aria-live="polite">
        <AnimatePresence initial={false}>
          {items.map((t) => (
            <motion.div key={t.id} layout className={cx(s.toast, t.kind === "success" ? s.toastSuccess : s.toastError)}
                        initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 24 }}
                        transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}>
              {t.kind === "success" ? <CircleCheck size={18} /> : <CircleAlert size={18} />}
              <span>{t.text}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  );
}

export function useToast(): ToastCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useToast phải nằm trong <ToastProvider>");
  return ctx;
}
