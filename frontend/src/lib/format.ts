import type { EventType, Gender, MemberType, RecordKind } from "../api/types";

const TZ = "Asia/Ho_Chi_Minh";

const dayFmt = new Intl.DateTimeFormat("vi-VN", { timeZone: TZ, weekday: "long", day: "2-digit", month: "2-digit" });
const timeFmt = new Intl.DateTimeFormat("vi-VN", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
const dateFmt = new Intl.DateTimeFormat("vi-VN", { timeZone: TZ, day: "2-digit", month: "2-digit", year: "numeric" });
const keyFmt = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });

export const fmtDay = (iso: string) => dayFmt.format(new Date(iso));
export const fmtTime = (iso: string) => timeFmt.format(new Date(iso));
export const fmtDate = (iso: string) => dateFmt.format(new Date(iso));
/** "2026-11-16" theo giờ Việt Nam — dùng để nhóm theo ngày */
export const dayKey = (iso: string) => keyFmt.format(new Date(iso));

export function relative(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "vừa xong";
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
  if (diff < 7 * 86400) return `${Math.floor(diff / 86400)} ngày trước`;
  return fmtDate(iso);
}

export const MEMBER_TYPE: Record<MemberType, string> = {
  self: "Bản thân", spouse: "Vợ/Chồng", child: "Con", parent: "Bố/Mẹ", sibling: "Anh/Chị/Em", other_relative: "Người thân",
};
export const GENDER: Record<Gender, string> = { male: "Nam", female: "Nữ", other: "Khác" };
export const RECORD_KIND: Record<RecordKind, string> = {
  condition: "Bệnh nền", medication: "Thuốc", allergy: "Dị ứng", lab_result: "Xét nghiệm",
};
export const EVENT_TYPE: Record<EventType, string> = {
  appointment: "Lịch khám", medication_reminder: "Nhắc uống thuốc", follow_up: "Tái khám",
};

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts.length > 1 ? parts[parts.length - 2][0] : "") + (parts[parts.length - 1]?.[0] ?? "")).toUpperCase();
}
