import { api } from "./client";
import type {
  CalendarEvent, ChatMessage, Dashboard, DocumentOut, EventType, Family, FamilyMember, MedicalRecord, MemberType,
  Occurrence, RecordKind, RegisterIn, User, UUID,
} from "./types";

export const auth = {
  login: (email: string, password: string) =>
    api<{ access_token: string }>("/auth/login", { body: new URLSearchParams({ username: email, password }) }),
  register: (data: RegisterIn) => api<User>("/auth/register", { body: data as unknown as Record<string, unknown> }),
  me: () => api<User>("/auth/me"),
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
