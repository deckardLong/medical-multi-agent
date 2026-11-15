import { useEffect, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import s from "./shell.module.css";

/** Popover nhẹ: đóng khi bấm ra ngoài hoặc Esc; animation chỉ dùng opacity + scale (transform). */
export function Popover({ trigger, children }: { trigger: (open: boolean, toggle: () => void) => ReactNode;
                                                 children: (close: () => void) => ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className={s.popWrap} ref={ref}>
      {trigger(open, () => setOpen((v) => !v))}
      <AnimatePresence>
        {open && (
          <motion.div className={s.pop} role="menu" initial={{ opacity: 0, scale: 0.96, y: -4 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.96, y: -4 }}
                      transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}>
            {children(() => setOpen(false))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
