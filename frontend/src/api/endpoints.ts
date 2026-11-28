import { api, ApiError } from "./client";
import type {
  CalendarEvent, ChatJob, ChatMessage, Dashboard, DocumentOut, EventType, Family, FamilyMember, MedicalRecord, MemberType,
  Occurrence, RecordKind, RegisterIn, User, UUID,
} from "./types";

export const auth = {
  login: (email: string, password: string) =>
    api<{ access_token: string }>("/auth/login", { body: new URLSearchParams({ username: email, password }) }),
  register: (data: RegisterIn) => api<User>("/auth/register", { body: data as unknown as Record<string, unknown> }),
  me: () => api<User>("/auth/me"),
  /** token: Google ID token hoặc Facebook access token — backend tự xác minh với nhà cung cấp */
  social: (provider: "google" | "facebook", token: string) =>
    api<{ access_token: string }>(`/auth/social/${provider}`, { body: { token } }),
  link: (provider: "google" | "facebook", token: string) =>
    api<void>(`/auth/social/${provider}/link`, { body: { token } }),
  linkedAccounts: () => api<{ provider: "google" | "facebook"; email: string | null }[]>("/auth/social/accounts"),
};

export const family = {
  mine: () => api<Family>("/families/me"),
  members: () => api<FamilyMember[]>("/families/me/members"),
  addMember: (data: { display_name: string; member_type: MemberType; dob?: string | null }) =>
    api<FamilyMember>("/families/me/members", { body: data }),
};

export const dashboard = {
  get: () => api<Dashboard>("/dashboard"),
};

const m = (memberId: UUID) => `/members/${memberId}`;

export const chat = {
  history: (memberId: UUID) => api<ChatMessage[]>(`${m(memberId)}/chat`),
  send: (memberId: UUID, content: string, documentIds: UUID[] = []) =>
    api<ChatMessage>(`${m(memberId)}/chat`, { body: { content, document_ids: documentIds } }),
  /**
   * Gửi câu hỏi chạy nền rồi hỏi kết quả mỗi 2.5s. Không request nào kéo dài, nên đi qua proxy cắt request dài
   * (Cloudflare Tunnel ~100s) vẫn được — đọc ảnh đơn thuốc trên CPU mất 3–5 phút.
   */
  ask: async (memberId: UUID, content: string, documentIds: UUID[] = [], opts: { signal?: AbortSignal } = {}) => {
    const job = await api<ChatJob>(`${m(memberId)}/chat/jobs`, { body: { content, document_ids: documentIds } });
    const deadline = Date.now() + 20 * 60 * 1000;
    for (;;) {
      await new Promise((r) => setTimeout(r, 2500));
      if (opts.signal?.aborted) throw new DOMException("aborted", "AbortError");
      const j = await api<ChatJob>(`${m(memberId)}/chat/jobs/${job.id}`, { signal: opts.signal });
      if (j.status === "done" && j.reply) return j.reply;
      if (j.status === "error") throw new ApiError(500, j.error ?? "AURELIA gặp lỗi khi xử lý câu hỏi.");
      if (Date.now() > deadline) throw new ApiError(504, "AURELIA trả lời quá lâu, vui lòng thử lại.");
    }
  },
};

export const avatars = {
  upload: (memberId: UUID, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api<FamilyMember>(`${m(memberId)}/avatar`, { method: "PUT", body: fd });
  },
  remove: (memberId: UUID) => api<FamilyMember>(`${m(memberId)}/avatar`, { method: "DELETE" }),
};

export const documents = {
  list: (memberId: UUID) => api<DocumentOut[]>(`${m(memberId)}/documents`),
  upload: (memberId: UUID, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api<DocumentOut>(`${m(memberId)}/documents`, { body: fd });
  },
};

export const records = {
  list: (memberId: UUID, status: "pending" | "confirmed" | "all") =>
    api<MedicalRecord[]>(`${m(memberId)}/records?status_filter=${status}`),
  create: (memberId: UUID, kind: RecordKind, payload: Record<string, string>) =>
    api<MedicalRecord>(`${m(memberId)}/records`, { body: { kind, payload } }),
  confirm: (memberId: UUID, id: UUID, payload?: Record<string, unknown>) =>
    api<MedicalRecord>(`${m(memberId)}/records/${id}/confirm`, { body: payload ? { payload } : {} }),
  remove: (memberId: UUID, id: UUID) => api<void>(`${m(memberId)}/records/${id}`, { method: "DELETE" }),
};

export const calendar = {
  occurrences: (memberId: UUID, opts: { start?: string; end?: string; includePending?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (opts.start) q.set("start", opts.start);
    if (opts.end) q.set("end", opts.end);
    if (opts.includePending) q.set("include_pending", "true");
    return api<Occurrence[]>(`${m(memberId)}/calendar?${q}`);
  },
  pending: (memberId: UUID) => api<CalendarEvent[]>(`${m(memberId)}/calendar/pending`),
  create: (memberId: UUID, data: { type: EventType; title: string; starts_at: string; recurrence_rule?: string | null }) =>
    api<CalendarEvent>(`${m(memberId)}/calendar`, { body: data }),
  confirm: (memberId: UUID, id: UUID) => api<CalendarEvent>(`${m(memberId)}/calendar/${id}/confirm`, { method: "POST" }),
  remove: (memberId: UUID, id: UUID) => api<void>(`${m(memberId)}/calendar/${id}`, { method: "DELETE" }),
};
