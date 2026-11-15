import { AnimatePresence, motion } from "framer-motion";
import { BellRing, FileScan, Moon, ShieldCheck, Sun } from "lucide-react";
import { Navigate, useLocation, useOutlet } from "react-router-dom";
import { Button } from "../../components/ui";
import { AureliaMark } from "../../components/AureliaMark";
import { useAuth } from "../../state/AuthContext";
import { useTheme } from "../../theme/ThemeProvider";
import s from "./auth.module.css";

export default function AuthLayout() {
  const { user } = useAuth();
  const { name, toggle } = useTheme();
  const location = useLocation();
  const outlet = useOutlet();             // giữ element cũ trong lúc exit animation (Outlet sẽ đổi ngay lập tức)
  if (user) return <Navigate to="/" replace />;

  return (
    <div className={s.page}>
      <div className={s.formSide}>
        <div className={s.formWrap}>
          <div className={s.brand}>
            <span className={s.brandMark}><AureliaMark size={26} /></span>
            <span className="gradient-text">AURELIA</span>
          </div>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div key={location.pathname}
                        initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }}
                        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}>
              {outlet}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <aside className={s.visual} aria-hidden>
        <div className={s.grid} />
        <div className={`${s.blob} ${s.blobA}`} />
        <div className={`${s.blob} ${s.blobB}`} />
        <div className={`${s.blob} ${s.blobC}`} />
        <div className={s.pulse}><AureliaMark size={128} /></div>
        <Button className={s.themeBtn} variant="secondary" size="sm" icon={name === "dark" ? Sun : Moon}
                onClick={(e) => toggle({ x: e.clientX, y: e.clientY })} aria-label="Đổi giao diện sáng/tối" />
        <div className={s.visualCopy}>
          <p className={s.fullName}>
            Assisted Understanding &amp; Reasoning for Evidence-based Life &amp; Integrated Assistance
          </p>
          <h2>Sức khoẻ cả nhà, <span className="gradient-text">gọn trong một nơi</span></h2>
          <p>AURELIA tra cứu tài liệu y khoa, đọc đơn thuốc và nhắc lịch — mọi thông tin chỉ có hiệu lực khi bạn xác nhận.</p>
          <ul className={s.features}>
            <li><span><FileScan size={16} /></span>Đọc đơn thuốc bằng 3 lần đọc độc lập rồi đối chiếu</li>
            <li><span><BellRing size={16} /></span>Nhắc lịch khám, uống thuốc qua email</li>
            <li><span><ShieldCheck size={16} /></span>Hồ sơ của mỗi người chỉ người đó (hoặc chủ gia đình) xem được</li>
          </ul>
        </div>
      </aside>
    </div>
  );
}
