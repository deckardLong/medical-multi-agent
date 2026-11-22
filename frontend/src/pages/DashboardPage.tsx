import { useState, type FormEvent } from "react";
import { motion } from "framer-motion";
import {
  CalendarClock, CircleAlert, ClipboardCheck, FileText, HeartPulse, Hourglass, Lock, MessageSquareText, Pill, ShieldAlert,
  Sparkles, Upload, UserPlus,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Avatar, Badge, Button, Card, Empty, Input, Modal, Select, Skeleton } from "../components/ui";
import { dashboard, family } from "../api/endpoints";
import type { MemberType } from "../api/types";
import { useAuth } from "../state/AuthContext";
import { useMembers } from "../state/MemberContext";
import { useToast } from "../state/ToastContext";
import { useAsync } from "../lib/useAsync";
import { AvatarUploader } from "../components/AvatarUploader";
import { EVENT_TYPE, MEMBER_TYPE, fmtDay, fmtTime, relative } from "../lib/format";
import s from "./pages.module.css";

// Thẻ xuất hiện lần lượt: stagger nhỏ (40ms) để có cảm giác "chảy" mà không làm chậm việc đọc
const list = { hidden: {}, show: { transition: { staggerChildren: 0.04 } } };
const item = { hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0, transition: { duration: 0.24, ease: [0.22, 1, 0.36, 1] } } };

function AddMemberModal({ open, onClose, onAdded }: { open: boolean; onClose: () => void; onAdded: () => void }) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [type, setType] = useState<MemberType>("child");
  const [dob, setDob] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await family.addMember({ display_name: name.trim(), member_type: type, dob: dob || null });
      toast.success(`Đã thêm ${name.trim()}`);
      setName(""); setDob("");
      onAdded();
      onClose();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Thêm thành viên">
      <form className={s.formGrid} onSubmit={submit}>
        <p className="muted" style={{ fontSize: 13 }}>
          Dành cho người chưa có tài khoản (con nhỏ, ông bà...). Bạn sẽ quản lý hồ sơ của họ.
        </p>
        <Input label="Tên hiển thị" placeholder="Bé Bin" value={name} onChange={(e) => setName(e.target.value)} autoFocus required />
        <div className={s.formRow}>
          <Select label="Quan hệ" value={type} onChange={(e) => setType(e.target.value as MemberType)}>
            {(Object.keys(MEMBER_TYPE) as MemberType[]).filter((t) => t !== "self").map((t) => (
              <option key={t} value={t}>{MEMBER_TYPE[t]}</option>
            ))}
          </Select>
          <Input label="Ngày sinh" type="date" max={new Date().toISOString().slice(0, 10)} value={dob}
                 onChange={(e) => setDob(e.target.value)} />
        </div>
        <div className={s.formFoot}>
          <Button type="button" variant="ghost" onClick={onClose}>Huỷ</Button>
          <Button type="submit" variant="primary" icon={UserPlus} loading={busy} disabled={!name.trim()}>Thêm</Button>
        </div>
      </form>
    </Modal>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { select, reload: reloadMembers } = useMembers();
  const navigate = useNavigate();
  const { data, error, loading, reload } = useAsync(() => dashboard.get(), []);
  const [adding, setAdding] = useState(false);

  const stats = data && [
    { icon: MessageSquareText, value: data.summary.consultations_this_month, label: "Lượt hỏi AURELIA tháng này", to: "/chat" },
    { icon: FileText, value: data.summary.documents_total, label: "Tài liệu đã tải lên", to: "/records" },
    { icon: CalendarClock, value: data.summary.upcoming_7d, label: "Lịch trong 7 ngày tới", to: "/calendar" },
    { icon: Hourglass, value: data.summary.pending_confirmations, label: "Đề xuất chờ xác nhận", to: "/records",
      accent: data.summary.pending_confirmations > 0 },
  ];

  return (
    <>
      <div className={s.head}>
        <div>
          <h1>Xin chào, <span className="gradient-text">{user?.first_name || user?.display_name}</span></h1>
          <p>Tình hình sức khoẻ của cả nhà hôm nay</p>
        </div>
        <div className={s.actions}>
          <Button icon={UserPlus} onClick={() => setAdding(true)}>Thêm thành viên</Button>
          <Button variant="primary" icon={Sparkles} onClick={() => navigate("/chat")}>Hỏi AURELIA</Button>
        </div>
      </div>

      {error && <Card><Empty icon={CircleAlert} title="Không tải được tổng quan">{error}</Empty></Card>}

      <motion.div className={s.stats} variants={list} initial="hidden" animate="show">
        {loading && !data
          ? [0, 1, 2, 3].map((i) => <Skeleton key={i} h={86} style={{ borderRadius: 24 }} />)
          : stats?.map(({ icon: Icon, value, label, to, accent }) => (
            <motion.div key={label} variants={item}>
              <Link to={to} className={s.statLink}>
                <Card tone={accent ? "accent" : "default"}>
                  <div className={s.stat}>
                    <span className={s.statIcon}><Icon size={20} /></span>
                    <div>
                      <div className={s.statValue}>{value}</div>
                      <div className={s.statLabel} style={accent ? { color: "inherit", opacity: 0.85 } : undefined}>{label}</div>
                    </div>
                  </div>
                </Card>
              </Link>
            </motion.div>
          ))}
      </motion.div>

      <div className={s.split}>
        <div className={s.stack}>
          <Card title="Thành viên gia đình" action={data && <Badge tone="info">{data.members.length} người</Badge>}>
            {loading && !data ? <Skeleton h={130} /> : (
              <motion.div className={s.memberGrid} variants={list} initial="hidden" animate="show">
                {data?.members.map((m) => (
                  <motion.div key={m.id} className={s.member} variants={item}>
                    <div className={s.memberHead}>
                      {m.health_visible
                        ? <AvatarUploader memberId={m.id} name={m.display_name} version={m.avatar_updated_at} size={44}
                                          onChanged={() => Promise.all([reload(), reloadMembers()])} />
                        : <Avatar name={m.display_name} size={44} memberId={m.id} version={m.avatar_updated_at} />}
                      <div className={s.grow}>
                        <strong>{m.display_name}</strong>
                        <small>{MEMBER_TYPE[m.member_type]}{m.age != null && ` · ${m.age} tuổi`}</small>
                      </div>
                    </div>
                    {m.health_visible ? (
                      <>
                        <div className={s.tags}>
                          {m.allergies?.map((a) => <Badge key={a} tone="danger" icon={ShieldAlert}>{a}</Badge>)}
                          {m.conditions?.map((c) => <Badge key={c} tone="warning" icon={HeartPulse}>{c}</Badge>)}
                          {!m.allergies?.length && !m.conditions?.length &&
                            <span className="muted" style={{ fontSize: 13 }}>Chưa ghi nhận dị ứng / bệnh nền</span>}
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span className="muted" style={{ fontSize: 13 }}><Pill size={13} /> {m.confirmed_records} mục hồ sơ</span>
                          <Button size="sm" variant="ghost" icon={Sparkles}
                                  onClick={() => { select(m.id); navigate("/chat"); }}>Hỏi</Button>
                        </div>
                      </>
                    ) : (
                      <div className={s.locked}><Lock size={14} />Người này tự quản lý hồ sơ sức khoẻ</div>
                    )}
                  </motion.div>
                ))}
              </motion.div>
            )}
          </Card>

          <Card title="Hoạt động gần đây">
            {loading && !data ? <Skeleton h={120} /> : !data?.timeline.length
              ? <Empty title="Chưa có hoạt động">Tải đơn thuốc lên hoặc xác nhận hồ sơ để thấy ở đây.</Empty>
              : (
                <ul className={s.list}>
                  {data.timeline.map((t, i) => (
                    <li key={i} className={s.listItem}>
                      <span className={s.statIcon} style={{ width: 36, height: 36, borderRadius: 11 }}>
                        {t.kind === "document_uploaded" ? <Upload size={16} /> : <ClipboardCheck size={16} />}
                      </span>
                      <div className={s.grow}>
                        <strong>{t.label}</strong>
                        <small>{t.member_name} · {relative(t.at)}</small>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
          </Card>
        </div>

        <Card title="Sắp tới" action={<Link to="/calendar" style={{ fontSize: 13 }}>Xem lịch</Link>}>
          {loading && !data ? <Skeleton h={200} /> : !data?.upcoming.length
            ? <Empty icon={CalendarClock} title="Không có lịch trong 7 ngày tới" />
            : (
              <ul className={s.list}>
                {data.upcoming.map((u, i) => (
                  <li key={i} className={s.listItem}>
                    <div className={s.when}><strong>{fmtTime(u.at)}</strong>{fmtDay(u.at).split(",")[0]}</div>
                    <div className={s.grow}>
                      <strong>{u.title}</strong>
                      <small>{u.member_name} · {EVENT_TYPE[u.type]}</small>
                    </div>
                    <span className={s.dot} />
                  </li>
                ))}
              </ul>
            )}
        </Card>
      </div>

      <AddMemberModal open={adding} onClose={() => setAdding(false)} onAdded={() => { reload(); reloadMembers(); }} />
    </>
  );
}
