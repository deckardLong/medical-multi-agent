import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Check, CircleAlert, ClipboardList, FileImage, FlaskConical, HeartPulse, Pill, Plus, ShieldAlert, Trash2, TriangleAlert,
  Upload, type LucideIcon,
} from "lucide-react";
import { Badge, Button, Card, ConfirmButton, Empty, Input, Modal, Select, Skeleton, Tabs } from "../components/ui";
import { documents, records } from "../api/endpoints";
import type { MedicalRecord, RecordKind } from "../api/types";
import { useMembers } from "../state/MemberContext";
import { useToast } from "../state/ToastContext";
import { useAsync } from "../lib/useAsync";
import { RECORD_KIND, fmtDate, relative } from "../lib/format";
import s from "./pages.module.css";

// Khớp records/service.py::UNRESOLVED — backend trả 409 khi xác nhận mà còn chuỗi này
const UNRESOLVED = "(cần kiểm tra)";
const KIND_ICON: Record<RecordKind, LucideIcon> = { condition: HeartPulse, medication: Pill, allergy: ShieldAlert, lab_result: FlaskConical };
const FIELD_VI: Record<string, string> = {
  name: "Tên", dose: "Liều", frequency: "Tần suất", duration: "Thời gian dùng", allergy: "Dị ứng", condition: "Bệnh",
  note: "Ghi chú", value: "Kết quả",
};

type Status = "pending" | "confirmed" | "all";

const asText = (v: unknown) => (typeof v === "string" ? v : JSON.stringify(v));
const isUnresolved = (v: unknown) => typeof v === "string" && v.includes(UNRESOLVED);
/** "30hrly | nocte (cần kiểm tra)" → ["30hrly", "nocte"] */
const options = (v: string) => v.replace(UNRESOLVED, "").split("|").map((x) => x.trim()).filter(Boolean);
const titleOf = (r: MedicalRecord) => asText(r.payload.name ?? Object.values(r.payload)[0] ?? RECORD_KIND[r.kind]).replace(UNRESOLVED, "").trim();

/* ---------- Gỡ trường đọc lệch rồi xác nhận ---------- */
function ResolveModal({ record, onClose, onDone, memberId }: {
  record: MedicalRecord | null; onClose: () => void; onDone: () => void; memberId: string;
}) {
  const toast = useToast();
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const fields = useMemo(() => Object.entries(record?.payload ?? {}), [record]);

  // Khởi tạo: trường đã rõ giữ nguyên; trường lệch để trống, bắt người dùng chọn
  useEffect(() => {
    if (record) setValues(Object.fromEntries(fields.map(([k, v]) => [k, isUnresolved(v) ? "" : asText(v)])));
  }, [record, fields]);

  const missing = fields.filter(([k, v]) => isUnresolved(v) && !values[k]?.trim()).length;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!record) return;
    setBusy(true);
    try {
      const payload = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, v.trim()]).filter(([, v]) => v));
      await records.confirm(memberId, record.id, payload);
      toast.success("Đã xác nhận vào hồ sơ");
      onDone();
      onClose();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={!!record} onClose={onClose} title="Kiểm tra và xác nhận">
      {record && (
        <form className={s.formGrid} onSubmit={submit}>
          <p className="muted" style={{ fontSize: 13 }}>
            Đối chiếu với đơn gốc. Những trường các lần đọc ảnh không thống nhất phải được chọn lại trước khi lưu.
          </p>
          {fields.map(([k, v]) => (
            <div key={k} className={s.formGrid} style={{ gap: 8 }}>
              <Input label={<>{FIELD_VI[k] ?? k}{isUnresolved(v) && <Badge tone="warning" icon={TriangleAlert}>Cần chọn</Badge>}</>}
                     value={values[k] ?? ""} onChange={(e) => setValues((x) => ({ ...x, [k]: e.target.value }))}
                     placeholder={isUnresolved(v) ? "Chọn bên dưới hoặc tự nhập" : undefined} />
              {isUnresolved(v) && (
                <div className={s.chips}>
                  {options(asText(v)).map((opt) => (
                    <button type="button" key={opt} className={`${s.chip} ${values[k] === opt ? s.chipActive : ""}`}
                            onClick={() => setValues((x) => ({ ...x, [k]: opt }))}>{opt}</button>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div className={s.formFoot}>
            <Button type="button" variant="ghost" onClick={onClose}>Huỷ</Button>
            <Button type="submit" variant="primary" icon={Check} loading={busy} disabled={missing > 0}>
              {missing ? `Còn ${missing} trường cần chọn` : "Xác nhận"}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

/* ---------- Người dùng tự nhập (có hiệu lực ngay) ---------- */
function AddRecordModal({ open, onClose, onDone, memberId }: { open: boolean; onClose: () => void; onDone: () => void; memberId: string }) {
  const toast = useToast();
  const [kind, setKind] = useState<RecordKind>("allergy");
  const [f, setF] = useState({ name: "", dose: "", frequency: "", note: "" });
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = Object.fromEntries(Object.entries(kind === "medication" ? f : { name: f.name, note: f.note })
        .map(([k, v]) => [k, v.trim()]).filter(([, v]) => v));
      await records.create(memberId, kind, payload);
      toast.success("Đã thêm vào hồ sơ");
      setF({ name: "", dose: "", frequency: "", note: "" });
      onDone();
      onClose();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Thêm mục hồ sơ">
      <form className={s.formGrid} onSubmit={submit}>
        <Select label="Loại" value={kind} onChange={(e) => setKind(e.target.value as RecordKind)}>
          {(Object.keys(RECORD_KIND) as RecordKind[]).map((k) => <option key={k} value={k}>{RECORD_KIND[k]}</option>)}
        </Select>
        <Input label={kind === "medication" ? "Tên thuốc" : kind === "allergy" ? "Dị nguyên" : "Tên"} autoFocus required
               value={f.name} onChange={(e) => setF((x) => ({ ...x, name: e.target.value }))}
               placeholder={kind === "allergy" ? "Penicillin" : kind === "medication" ? "Paracetamol" : ""} />
        {kind === "medication" && (
          <div className={s.formRow}>
            <Input label="Liều" placeholder="500 mg" value={f.dose} onChange={(e) => setF((x) => ({ ...x, dose: e.target.value }))} />
            <Input label="Tần suất" placeholder="2 lần/ngày" value={f.frequency} onChange={(e) => setF((x) => ({ ...x, frequency: e.target.value }))} />
          </div>
        )}
        <Input label="Ghi chú" value={f.note} onChange={(e) => setF((x) => ({ ...x, note: e.target.value }))} />
        <div className={s.formFoot}>
          <Button type="button" variant="ghost" onClick={onClose}>Huỷ</Button>
          <Button type="submit" variant="primary" icon={Plus} loading={busy} disabled={!f.name.trim()}>Thêm</Button>
        </div>
      </form>
    </Modal>
  );
}

export default function RecordsPage() {
  const { current } = useMembers();
  const toast = useToast();
  const memberId = current?.id;
  const [status, setStatus] = useState<Status>("pending");
  const [resolving, setResolving] = useState<MedicalRecord | null>(null);
  const [adding, setAdding] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const list = useAsync(() => (memberId ? records.list(memberId, status) : Promise.resolve([])), [memberId, status]);
  const docs = useAsync(() => (memberId ? documents.list(memberId) : Promise.resolve([])), [memberId]);

  async function confirmQuick(r: MedicalRecord) {
    if (!memberId) return;
    if (Object.values(r.payload).some(isUnresolved)) return setResolving(r);
    setBusyId(r.id);
    try {
      await records.confirm(memberId, r.id);
      toast.success("Đã xác nhận vào hồ sơ");
      list.reload();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  async function remove(r: MedicalRecord) {
    if (!memberId) return;
    setBusyId(r.id);
    try {
      await records.remove(memberId, r.id);
      list.setData((xs) => (xs ?? []).filter((x) => x.id !== r.id));
      toast.success("Đã xoá");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  async function upload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !memberId) return;
    setUploading(true);
    try {
      await documents.upload(memberId, file);
      toast.success("Đã tải ảnh lên. Gửi kèm ảnh khi chat với AURELIA để đọc đơn.");
      docs.reload();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setUploading(false);
    }
  }

  if (!current || !memberId) return <Skeleton h={300} />;

  return (
    <>
      <div className={s.head}>
        <div>
          <h1>Hồ sơ của {current.display_name}</h1>
          <p>Chỉ những mục đã xác nhận mới được AURELIA dùng để tư vấn</p>
        </div>
        <div className={s.actions}>
          <Tabs id="rec-status" value={status} onChange={setStatus}
                items={[{ value: "pending", label: "Chờ xác nhận" }, { value: "confirmed", label: "Đã xác nhận" }, { value: "all", label: "Tất cả" }]} />
          <Button variant="primary" icon={Plus} onClick={() => setAdding(true)}>Thêm mục</Button>
        </div>
      </div>

      <div className={s.split}>
        <Card>
          {list.error && <Empty icon={CircleAlert} title="Không tải được hồ sơ">{list.error}</Empty>}
          {list.loading && !list.data ? <div className={s.stack}><Skeleton h={110} /><Skeleton h={110} /></div>
            : !list.data?.length ? (
              <Empty icon={ClipboardList} title={status === "pending" ? "Không có đề xuất nào chờ xác nhận" : "Chưa có mục hồ sơ"}>
                {status === "pending" ? "Gửi ảnh đơn thuốc cho AURELIA để tạo đề xuất." : "Bấm \"Thêm mục\" để tự nhập."}
              </Empty>
            ) : (
              <div className={s.stack}>
                <AnimatePresence initial={false}>
                  {list.data.map((r) => {
                    const Icon = KIND_ICON[r.kind];
                    const flagged = Object.values(r.payload).filter(isUnresolved).length;
                    return (
                      <motion.div key={r.id} className={s.recordCard} layout
                                  initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: 24 }}
                                  transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}>
                        <div className={s.recordHead}>
                          <span className={s.statIcon} style={{ width: 36, height: 36, borderRadius: 11 }}><Icon size={17} /></span>
                          <h4>{titleOf(r)}</h4>
                          <Badge tone={r.kind === "allergy" ? "danger" : "info"}>{RECORD_KIND[r.kind]}</Badge>
                          {r.source_document_id && <Badge icon={FileImage}>Từ ảnh</Badge>}
                          {r.confirmed_at ? <Badge tone="success" icon={Check}>Xác nhận {fmtDate(r.confirmed_at)}</Badge>
                            : flagged ? <Badge tone="warning" icon={TriangleAlert}>{flagged} trường cần kiểm tra</Badge>
                            : <Badge tone="warning">Chờ xác nhận</Badge>}
                        </div>
                        <div className={s.fields}>
                          {Object.entries(r.payload).map(([k, v]) => (
                            <div key={k} className={`${s.fieldBox} ${isUnresolved(v) ? s.fieldUnresolved : ""}`}>
                              <small>{FIELD_VI[k] ?? k}</small>{asText(v).replace(UNRESOLVED, "").trim()}
                            </div>
                          ))}
                        </div>
                        <div className={s.rowActions}>
                          <ConfirmButton icon={Trash2} onConfirm={() => remove(r)} />
                          {!r.confirmed_at && (
                            <Button size="sm" variant="primary" icon={Check} loading={busyId === r.id} onClick={() => confirmQuick(r)}>
                              {flagged ? "Kiểm tra & xác nhận" : "Xác nhận"}
                            </Button>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>
            )}
        </Card>

        <Card title="Ảnh đã tải lên" action={
          <>
            <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={upload} />
            <Button size="sm" icon={Upload} loading={uploading} onClick={() => fileRef.current?.click()}>Tải ảnh</Button>
          </>
        }>
          {docs.loading && !docs.data ? <Skeleton h={120} /> : !docs.data?.length ? (
            <Empty icon={FileImage} title="Chưa có ảnh nào">JPEG, PNG hoặc WEBP, tối đa 10MB.</Empty>
          ) : (
            <ul className={s.list}>
              {docs.data.map((d) => (
                <li key={d.id} className={s.listItem}>
                  <span className={s.statIcon} style={{ width: 36, height: 36, borderRadius: 11 }}><FileImage size={16} /></span>
                  <div className={s.grow}>
                    <strong>Ảnh {d.mime_type.replace("image/", "").toUpperCase()}</strong>
                    <small>{relative(d.created_at)}</small>
                  </div>
                  {d.extracted_json ? <Badge tone="success">Đã đọc</Badge> : <Badge>Chưa đọc</Badge>}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <ResolveModal record={resolving} onClose={() => setResolving(null)} onDone={list.reload} memberId={memberId} />
      <AddRecordModal open={adding} onClose={() => setAdding(false)} onDone={list.reload} memberId={memberId} />
    </>
  );
}
