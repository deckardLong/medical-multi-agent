import { lazy } from "react";

const loaders = {
  dashboard: () => import("./DashboardPage"),
  chat: () => import("./ChatPage"),
  calendar: () => import("./CalendarPage"),
  records: () => import("./RecordsPage"),
};

export const DashboardPage = lazy(loaders.dashboard);
export const ChatPage = lazy(loaders.chat);
export const CalendarPage = lazy(loaders.calendar);
export const RecordsPage = lazy(loaders.records);

/** Gọi khi trình duyệt rảnh: import() lần hai dùng lại module đã tải nên chuyển trang không còn chờ mạng. */
export function prefetchPages() {
  Object.values(loaders).forEach((load) => load().catch(() => undefined));
}
