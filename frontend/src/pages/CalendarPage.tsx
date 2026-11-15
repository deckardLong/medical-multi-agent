import { useMemo, useState, type FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, CalendarCheck2, CalendarPlus, Check, CircleAlert, Clock, Repeat, Trash2 } from "lucide-react";
import { Badge, Button, Card, ConfirmButton, Empty, Input, Modal, Select, Skeleton, Tabs } from "../components/ui";
import { calendar } from "../api/endpoints";
import type { EventType, Occurrence } from "../api/types";
import { useMembers } from "../state/MemberContext";
import { useToast } from "../state/ToastContext";
import { useAsync } from "../lib/useAsync";
import { EVENT_TYPE, dayKey, fmtDate, fmtDay, fmtTime } from "../lib/format";
import s from "./pages.module.css";

type Range = "7" | "30" | "90";
type Repeat = "none" | "daily" | "hourly" | "weekly" | "custom";

function buildRule(repeat: Repeat, count: number, hours: number, custom: string): string | null {
  switch (repeat) {
    case "daily": return `FREQ=DAILY;COUNT=${count}`;
    case "hourly": return `FREQ=HOURLY;INTERVAL=${hours};COUNT=${count}`;
    case "weekly": return `FREQ=WEEKLY;COUNT=${count}`;
    case "custom": return custom.trim() || null;
    default: return null;
  }
}

function describeRule(rule: string | null): string | null {
  if (!rule) return null;
  const count = /COUNT=(\d+)/.exec(rule)?.[1];
  const interval = /INTERVAL=(\d+)/.exec(rule)?.[1];
  const tail = count ? ` · ${count} lần` : "";
  if (rule.includes("FREQ=DAILY")) return `Hằng ngày${tail}`;
  if (rule.includes("FREQ=HOURLY")) return `Mỗi ${interval ?? 1} giờ${tail}`;
  if (rule.includes("FREQ=WEEKLY")) return `Hằng tuần${tail}`;
  return "Lặp lại";
}

function CreateEventModal({ open, onClose, onCreated, memberId }: {
  open: boolean; onClose: () => void; onCreated: () => void; memberId: string;
}) {
  const toast = useToast();
  const [type, setType] = useState<EventType>("medication_reminder");
  const [title, setTitle] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [repeat, setRepeat] = useState<Repeat>("none");
  const [count, setCount] = useState(7);
  const [hours, setHours] = useState(8);
  const [custom, setCustom] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      // datetime-local không kèm múi giờ → backend hiểu là giờ Việt Nam
      await calendar.create(memberId, { type, title: title.trim(), starts_at: startsAt,
                                        recurrence_rule: buildRule(repeat, count, hours, custom) });
      toast.success("Đã tạo lịch");
      setTitle(""); setStartsAt(""); setRepeat("none");
      onCreated();
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Tạo lịch mới">
      <form className={s.formGrid} onSubmit={submit}>
        <div className={s.formRow}>
          <Select label="Loại" value={type} onChange={(e) => setType(e.target.value as EventType)}>
            {(Object.keys(EVENT_TYPE) as EventType[]).map((t) => <option key={t} value={t}>{EVENT_TYPE[t]}</option>)}
          </Select>
          <Input label="Bắt đầu" type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} required />
        </div>
        <Input label="Tiêu đề" placeholder="Uống thuốc hạ sốt" value={title} onChange={(e) => setTitle(e.target.value)}
               maxLength={200} autoFocus required />
        <Select label="Lặp lại" value={repeat} onChange={(e) => setRepeat(e.target.value as Repeat)}>
          <option value="none">Không lặp</option>
          <option value="daily">Hằng ngày</option>
          <option value="hourly">Mỗi N giờ</option>
          <option value="weekly">Hằng tuần</option>
          <option value="custom">Tự nhập RRULE</option>
        </Select>
        {repeat !== "none" && repeat !== "custom" && (
          <div className={s.formRow}>
            <Input label="Số lần" type="number" min={1} max={366} value={count} onChange={(e) => setCount(+e.target.value || 1)} />
            {repeat === "hourly" &&
              <Input label="Cách nhau (giờ)" type="number" min={1} max={24} value={hours} onChange={(e) => setHours(+e.target.value || 1)} />}
          </div>
        )}
        {repeat === "custom" && (
          <Input label="RRULE" placeholder="FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=6" value={custom}
                 onChange={(e) => setCustom(e.target.value)} hint="Theo chuẩn RFC 5545" />
        )}
        {error && <span style={{ color: "var(--c-danger)", fontSize: 13 }}><CircleAlert size={14} /> {error}</span>}
        <div className={s.formFoot}>
          <Button type="button" variant="ghost" onClick={onClose}>Huỷ</Button>
          <Button type="submit" variant="primary" icon={CalendarPlus} loading={busy} disabled={!title.trim() || !startsAt}>Tạo lịch</Button>
        </div>
      </form>
    </Modal>
  );
}

export default function CalendarPage() {
  const { current } = useMembers();
  const toast = useToast();
  const memberId = current?.id;
  const [range, setRange] = useState<Range>("30");
  const [withPending, setWithPending] = useState(false);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const occ = useAsync(() => {
    if (!memberId) return Promise.resolve([] as Occurrence[]);
    const start = new Date();
    const end = new Date(start.getTime() + +range * 86400_000);
    return calendar.occurrences(memberId, { start: start.toISOString(), end: end.toISOString(), includePending: withPending });
  }, [memberId, range, withPending]);
  const pending = useAsync(() => (memberId ? calendar.pending(memberId) : Promise.resolve([])), [memberId]);

  const groups = useMemo(() => {
    const map = new Map<string, Occurrence[]>();
    for (const o of occ.data ?? []) map.set(dayKey(o.occurs_at), [...(map.get(dayKey(o.occurs_at)) ?? []), o]);
    return [...map.entries()];
  }, [occ.data]);

  async function act(id: string, fn: () => Promise<unknown>, okText: string) {
    setBusyId(id);
    try {
      await fn();
      toast.success(okText);
      await Promise.all([occ.reload(), pending.reload()]);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  if (!current || !memberId) return <Skeleton h={300} />;

  return (
    <>
      <div className={s.head}>
        <div>
          <h1>Lịch của {current.display_name}</h1>
          <p>Lịch khám, tái khám và nhắc uống thuốc — lịch lặp được hiển thị thành từng lần</p>
        </div>
        <div className={s.actions}>
          <Tabs id="cal-range" value={range} onChange={setRange}
                items={[{ value: "7", label: "7 ngày" }, { value: "30", label: "30 ngày" }, { value: "90", label: "90 ngày" }]} />
          <Button variant="primary" icon={CalendarPlus} onClick={() => setCreating(true)}>Tạo lịch</Button>
        </div>
      </div>

      <div className={s.split}>
        <Card title="Sắp diễn ra" action={
          <label style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={withPending} onChange={(e) => setWithPending(e.target.checked)}
                   style={{ accentColor: "var(--c-accent)" }} />
            Hiện cả đề xuất chưa xác nhận
          </label>
        }>
          {occ.error && <Empty icon={CircleAlert} title="Không tải được lịch">{occ.error}</Empty>}
          {occ.loading && !occ.data ? <Skeleton h={220} /> : !groups.length ? (
            <Empty icon={CalendarCheck2} title={`Không có lịch trong ${range} ngày tới`}>
              Bấm "Tạo lịch" hoặc nhờ AURELIA đặt lịch nhắc uống thuốc.
            </Empty>
          ) : (
            <motion.div layout>
              {groups.map(([day, items]) => (
                <div key={day} className={s.dayGroup}>
                  <h4 className={s.dayTitle}>{fmtDay(items[0].occurs_at)}</h4>
                  <ul className={s.list}>
                    {items.map((o) => (
                      <li key={o.event_id + o.occurs_at} className={s.listItem}>
                        <div className={s.when}><strong>{fmtTime(o.occurs_at)}</strong>{fmtDate(o.occurs_at).slice(0, 5)}</div>
                        <div className={s.grow}>
                          <strong>{o.title}</strong>
                          <small>{EVENT_TYPE[o.type]}</small>
                        </div>
                        {o.recurrence_rule && <Badge tone="info" icon={Repeat}>{describeRule(o.recurrence_rule)}</Badge>}
                        {!o.confirmed && <Badge tone="warning" icon={Clock}>Chờ xác nhận</Badge>}
                        <ConfirmButton icon={Trash2} loading={busyId === o.event_id}
                                       confirmText={o.recurrence_rule ? "Xoá cả chuỗi?" : "Chắc chắn?"}
                                       onConfirm={() => act(o.event_id, () => calendar.remove(memberId, o.event_id), "Đã xoá lịch")} />
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </motion.div>
          )}
        </Card>

        <Card title="Chờ xác nhận" action={pending.data && <Badge tone={pending.data.length ? "warning" : "neutral"}>{pending.data.length}</Badge>}>
          <p className="muted" style={{ fontSize: 13, marginBottom: 10 }}>
            Lịch do AURELIA đề xuất chỉ có hiệu lực (và chỉ được nhắc qua email) sau khi bạn xác nhận.
          </p>
          {pending.loading && !pending.data ? <Skeleton h={120} /> : !pending.data?.length ? (
            <Empty icon={Check} title="Không có đề xuất nào" />
          ) : (
            <ul className={s.list}>
              <AnimatePresence initial={false}>
                {pending.data.map((ev) => (
                  <motion.li key={ev.id} className={s.listItem} style={{ flexWrap: "wrap" }} layout
                             initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, x: 20 }}>
                    <div className={s.grow}>
                      <strong>{ev.title}</strong>
                      <small>
                        {fmtDay(ev.starts_at)} · {fmtTime(ev.starts_at)}
                        {ev.recurrence_rule && ` · ${describeRule(ev.recurrence_rule)}`}
                      </small>
                    </div>
                    {ev.source === "agent" && <Badge tone="info" icon={Bot}>AI</Badge>}
                    <div className={s.rowActions} style={{ width: "100%" }}>
                      <ConfirmButton icon={Trash2} onConfirm={() => act(ev.id, () => calendar.remove(memberId, ev.id), "Đã bỏ đề xuất")}>Bỏ</ConfirmButton>
                      <Button size="sm" variant="primary" icon={Check} loading={busyId === ev.id}
                              onClick={() => act(ev.id, () => calendar.confirm(memberId, ev.id), "Đã xác nhận lịch")}>Xác nhận</Button>
                    </div>
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          )}
        </Card>
      </div>

      <CreateEventModal open={creating} onClose={() => setCreating(false)} memberId={memberId}
                        onCreated={() => { occ.reload(); }} />
    </>
  );
}
