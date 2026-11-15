import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight, Bot, CircleAlert, FileImage, Hourglass, ImagePlus, MessageSquareText, Paperclip, SendHorizontal,
  ShieldAlert, Sparkles, X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Avatar, Badge, Button, Card, Empty, Skeleton } from "../components/ui";
import { Markdown } from "../components/Markdown";
import { calendar, chat, dashboard, documents, records } from "../api/endpoints";
import type { ChatMessage } from "../api/types";
import { useMembers } from "../state/MemberContext";
import { useToast } from "../state/ToastContext";
import { useAsync } from "../lib/useAsync";
import { MEMBER_TYPE } from "../lib/format";
import s from "./chat.module.css";

const MAX_FILE = 10 * 1024 * 1024;
const ACCEPT = ["image/jpeg", "image/png", "image/webp"];

interface Pending { file: File; url: string }

export default function ChatPage() {
  const { current } = useMembers();
  const toast = useToast();
  const navigate = useNavigate();
  const memberId = current?.id;

  const history = useAsync(() => (memberId ? chat.history(memberId) : Promise.resolve([])), [memberId]);
  const overview = useAsync(() => dashboard.get(), []);
  const pending = useAsync(async () => {
    if (!memberId) return 0;
    const [r, e] = await Promise.all([records.list(memberId, "pending"), calendar.pending(memberId)]);
    return r.length + e.length;
  }, [memberId]);

  const [text, setText] = useState("");
  const [files, setFiles] = useState<Pending[]>([]);
  const [sending, setSending] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const threadRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const activeMember = useRef(memberId);
  activeMember.current = memberId;

  const messages = history.data ?? [];
  const card = overview.data?.members.find((m) => m.id === memberId);

  // Cuộn xuống cuối khi có tin mới — layout effect để không thấy khung hình "nhảy"
  useLayoutEffect(() => {
    const el = threadRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length, sending]);

  useEffect(() => {
    if (!sending) return;
    setElapsed(0);
    const t = setInterval(() => setElapsed((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, [sending]);

  const filesRef = useRef(files);
  filesRef.current = files;
  useEffect(() => () => filesRef.current.forEach((f) => URL.revokeObjectURL(f.url)), []);   // dọn object URL khi rời trang

  function autosize() {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  function pickFiles(e: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(e.target.files ?? []);
    e.target.value = "";
    const ok: Pending[] = [];
    for (const f of picked) {
      if (!ACCEPT.includes(f.type)) toast.error(`${f.name}: chỉ nhận ảnh JPEG, PNG hoặc WEBP`);
      else if (f.size > MAX_FILE) toast.error(`${f.name}: ảnh vượt quá 10MB`);
      else ok.push({ file: f, url: URL.createObjectURL(f) });
    }
    setFiles((xs) => [...xs, ...ok].slice(0, 3));
  }

  function removeFile(url: string) {
    URL.revokeObjectURL(url);
    setFiles((xs) => xs.filter((f) => f.url !== url));
  }

  async function send() {
    const content = text.trim() || (files.length ? "Đọc giúp tôi đơn thuốc này" : "");
    if (!memberId || !content || sending) return;
    const forMember = memberId;
    const sentFiles = files;
    const optimistic: ChatMessage = { id: `tmp-${Date.now()}`, role: "user", content,
                                      attachments: sentFiles.length ? sentFiles.map((f) => f.url) : null };
    history.setData([...messages, optimistic]);
    setText("");
    setFiles([]);
    requestAnimationFrame(autosize);
    setSending(true);
    try {
      const ids = await Promise.all(sentFiles.map((f) => documents.upload(forMember, f.file).then((d) => d.id)));
      await chat.send(forMember, content, ids);
      if (activeMember.current !== forMember) return;      // đã đổi sang thành viên khác trong lúc chờ
      await history.reload();                              // lấy lại từ server: có id thật + câu trả lời đã lưu
      if (ids.length) pending.reload();
    } catch (err) {
      toast.error((err as Error).message);
      if (activeMember.current === forMember) {
        history.setData((xs) => (xs ?? []).filter((m) => m.id !== optimistic.id));
        setText(content);
        setFiles(sentFiles);
        return;
      }
    } finally {
      setSending(false);
    }
    sentFiles.forEach((f) => URL.revokeObjectURL(f.url));
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {   // isComposing: đang gõ dấu tiếng Việt (IME)
      e.preventDefault();
      send();
    }
  }

  function jumpTo(id: string) {
    const el = document.getElementById(`msg-${id}`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.remove(s.flash);
    void el.offsetWidth;                               // khởi động lại animation nhấp nháy
    el.classList.add(s.flash);
  }

  const questions = useMemo(() => messages.filter((m) => m.role === "user" && !m.id.startsWith("tmp-")).reverse(), [messages]);
  const docsSent = messages.filter((m) => m.attachments?.length).length;

  if (!current) return <Skeleton h={400} />;

  return (
    <div className={s.layout}>
      {/* ---------- Cột trái ---------- */}
      <div className={s.col}>
        <Card>
          <div className={s.eyebrow}><span>Trợ lý AI của bạn</span><Badge tone="info">Qwen 2.5</Badge></div>
          <h2 className={s.doctor}>Bác sĩ gia đình</h2>
          <p className={s.disclaimer}>
            Trợ lý không thay thế bác sĩ. Hãy hỏi ý kiến chuyên gia y tế trước khi dùng thuốc; tự điều trị có thể
            gây hại cho sức khoẻ.
          </p>
          <Button variant="primary" block icon={ImagePlus} onClick={() => fileRef.current?.click()}>Gửi ảnh đơn thuốc</Button>
        </Card>
        <Card className={s.col} title="Câu hỏi gần đây">
          <div className={s.history}>
            {history.loading && !history.data ? <Skeleton h={120} />
              : !questions.length ? <Empty icon={MessageSquareText} title="Chưa có câu hỏi" />
              : questions.map((q) => (
                <button key={q.id} className={s.histItem} title={q.content} onClick={() => jumpTo(q.id)}>{q.content}</button>
              ))}
          </div>
        </Card>
      </div>

      {/* ---------- Cột giữa ---------- */}
      <div className={s.col}>
        <div className={s.chatHead}>
          <h2>Trò chuyện với trợ lý</h2>
          <Badge tone="success">Đang hỏi cho: {current.display_name}</Badge>
        </div>

        <div className={s.thread} ref={threadRef} aria-live="polite">
          {history.error && <Empty icon={CircleAlert} title="Không tải được lịch sử">{history.error}</Empty>}
          {history.loading && !history.data && <><Skeleton h={60} w="70%" /><Skeleton h={90} w="80%" style={{ alignSelf: "flex-end" }} /></>}
          {history.data && !messages.length && !sending && (
            <Empty icon={Sparkles} title={`Bắt đầu hỏi về sức khoẻ của ${current.display_name}`}>
              Ví dụ: "Bé bị sốt 38.5 độ nên làm gì?", hoặc gửi ảnh đơn thuốc để trợ lý đọc và tạo đề xuất hồ sơ.
            </Empty>
          )}
          <AnimatePresence initial={false}>
            {messages.map((m) => (
              <motion.div key={m.id} id={`msg-${m.id}`} className={`${s.msg} ${m.role === "user" ? s.msgUser : ""}`}
                          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}>
                {m.role === "user" ? <Avatar name={current.display_name} size={34} /> : <span className={s.badgeOk}><Bot size={18} /></span>}
                <div className={`${s.bubble} ${m.role === "user" ? s.bubbleUser : ""}`}>
                  {m.role === "assistant" ? <Markdown text={m.content} /> : m.content}
                  {!!m.attachments?.length && (
                    <div className={s.attach}><Paperclip size={13} />{m.attachments.length} ảnh đính kèm</div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {sending && (
            <motion.div className={s.typing} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <span className={s.badgeOk}><Bot size={18} /></span>
              <span className={s.dots}><i /><i /><i /></span>
              Trợ lý đang soạn trả lời · {elapsed}s
              {elapsed > 20 && <span>(chạy trên CPU, đọc ảnh đơn thuốc có thể mất 3–5 phút)</span>}
            </motion.div>
          )}
        </div>

        <div className={s.composer}>
          <input ref={fileRef} type="file" accept={ACCEPT.join(",")} multiple hidden onChange={pickFiles} />
          <Button icon={FileImage} onClick={() => fileRef.current?.click()} aria-label="Đính kèm ảnh đơn thuốc"
                  disabled={sending || files.length >= 3} />
          <div className={s.inputBox}>
            {!!files.length && (
              <div className={s.files}>
                {files.map((f) => (
                  <div key={f.url} className={s.file}>
                    <img src={f.url} alt={f.file.name} />
                    <button onClick={() => removeFile(f.url)} aria-label={`Bỏ ${f.file.name}`}><X size={12} /></button>
                  </div>
                ))}
              </div>
            )}
            <textarea ref={inputRef} rows={1} value={text} placeholder="Nhập câu hỏi... (Enter để gửi, Shift+Enter xuống dòng)"
                      onChange={(e) => { setText(e.target.value); autosize(); }} onKeyDown={onKey} disabled={sending} />
          </div>
          <Button variant="primary" icon={SendHorizontal} onClick={send} loading={sending}
                  disabled={!text.trim() && !files.length}>Gửi</Button>
        </div>
      </div>

      {/* ---------- Cột phải ---------- */}
      <div className={s.col}>
        <Card>
          <div className={s.eyebrow}><span>Hồ sơ đang xem</span></div>
          <div style={{ marginTop: 14 }}><Avatar name={current.display_name} size={64} /></div>
          <h3 className={s.profileName}>{current.display_name}</h3>
          <div className={s.meta}>
            <span>{MEMBER_TYPE[current.member_type]}</span>
            {card?.age != null && <><span>•</span><span>{card.age} tuổi</span></>}
          </div>
          {card?.health_visible === false ? (
            <p className="muted" style={{ fontSize: 13 }}>Người này tự quản lý hồ sơ sức khoẻ.</p>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
              {card?.allergies?.map((a) => <Badge key={a} tone="danger" icon={ShieldAlert}>Dị ứng: {a}</Badge>)}
              {card?.conditions?.map((c) => <Badge key={c} tone="warning">{c}</Badge>)}
              {card && !card.allergies?.length && !card.conditions?.length &&
                <span className="muted" style={{ fontSize: 13 }}>Chưa ghi nhận dị ứng hay bệnh nền.</span>}
            </div>
          )}
          <div className={s.kv}><span>Câu hỏi đã gửi</span><span>{questions.length}</span></div>
          <div className={s.kv}><span>Lần gửi kèm ảnh</span><span>{docsSent}</span></div>
          <div className={s.kv}><span>Mục hồ sơ đã xác nhận</span><span>{card?.confirmed_records ?? "—"}</span></div>
        </Card>
        <Card tone="accent">
          <div className={s.eyebrow} style={{ color: "inherit", opacity: 0.8 }}><span>Cần bạn xem lại</span><Hourglass size={14} /></div>
          <h3 style={{ fontSize: 22, margin: "6px 0 4px" }}>
            <span style={{ fontFamily: "var(--font-body)", fontVariantNumeric: "tabular-nums" }}>{pending.data ?? 0}</span> đề xuất
          </h3>
          <p style={{ fontSize: 13, opacity: 0.85, marginBottom: 14 }}>
            Trợ lý chỉ tạo đề xuất. Hồ sơ và lịch chỉ có hiệu lực khi bạn xác nhận.
          </p>
          <Button block icon={ArrowRight} onClick={() => navigate("/records")}>Xem đề xuất</Button>
        </Card>
      </div>
    </div>
  );
}
