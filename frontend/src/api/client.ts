// Dev: "/api" (Vite proxy sang FastAPI, cùng origin). Deploy: VITE_API_BASE=https://<backend>.onrender.com
export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/+$/, "") || "/api";
const BASE = API_BASE;
const TOKEN_KEY = "fh.token";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// "Ghi nhớ đăng nhập" → localStorage (còn sau khi đóng trình duyệt); không → sessionStorage (mất khi đóng tab)
export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string, remember: boolean) {
    try {
      (remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, token);
      (remember ? sessionStorage : localStorage).removeItem(TOKEN_KEY);
    } catch { /* bộ nhớ trình duyệt bị chặn: chỉ giữ trong phiên hiện tại qua state */ }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem(TOKEN_KEY);
    } catch { /* bỏ qua */ }
  },
};

let onUnauthorized: () => void = () => undefined;
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

const FIELD_VI: Record<string, string> = {
  email: "Email", password: "Mật khẩu", first_name: "Tên", last_name: "Họ", date_of_birth: "Ngày sinh",
  phone: "Số điện thoại", title: "Tiêu đề", starts_at: "Thời gian", payload: "Nội dung", content: "Nội dung",
};

/** FastAPI trả detail là chuỗi, hoặc danh sách lỗi (422) → gộp thành một câu đọc được. */
function messageFrom(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: (string | number)[]; msg?: string }) => {
        const field = String(d.loc?.[d.loc.length - 1] ?? "");
        return `${FIELD_VI[field] ?? field}: ${(d.msg ?? "").replace(/^Value error, /, "")}`;
      })
      .join(" · ");
  }
  if (status >= 500) return "Máy chủ đang gặp sự cố, vui lòng thử lại sau.";
  return `Yêu cầu thất bại (${status})`;
}

type Body = BodyInit | Record<string, unknown> | unknown[] | undefined;

export async function api<T>(path: string, opts: { method?: string; body?: Body; signal?: AbortSignal } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (opts.body instanceof FormData || opts.body instanceof URLSearchParams) body = opts.body;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(BASE + path, { method: opts.method ?? (body ? "POST" : "GET"), headers, body, signal: opts.signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, import.meta.env.DEV ? "Không kết nối được máy chủ. Kiểm tra backend (cổng 8000) đã chạy chưa."
                                               : "Không kết nối được máy chủ. Máy chủ có thể đang khởi động, vui lòng thử lại sau ít phút.");
  }

  if (res.status === 401 && token) onUnauthorized();
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, messageFrom(res.status, data));
  return data as T;
}
