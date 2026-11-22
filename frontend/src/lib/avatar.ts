import { useEffect, useState } from "react";
import { API_BASE, tokenStore } from "../api/client";
import type { UUID } from "../api/types";

/**
 * Ảnh đại diện phục vụ qua GET /members/{id}/avatar có kiểm tra quyền → thẻ <img src> không gửi được header
 * Authorization, nên tải bằng fetch rồi dùng object URL. Cache theo (thành viên, phiên bản): cùng một avatar
 * hiện ở nhiều chỗ (menu, dashboard, bong bóng chat) chỉ tải một lần; đổi ảnh → avatar_updated_at đổi → khoá mới.
 */
const cache = new Map<string, Promise<string | null>>();

function load(memberId: UUID, version: string): Promise<string | null> {
  const key = `${memberId}:${version}`;
  let p = cache.get(key);
  if (!p) {
    const token = tokenStore.get();
    p = fetch(`${API_BASE}/members/${memberId}/avatar?v=${encodeURIComponent(version)}`,
              { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => (r.ok ? r.blob() : null))
      .then((b) => (b ? URL.createObjectURL(b) : null))
      .catch(() => null);
    p.then((url) => { if (!url) cache.delete(key); });   // lỗi mạng → lần sau thử lại, không cache thất bại
    cache.set(key, p);
  }
  return p;
}

/** Trả object URL của avatar, hoặc null khi chưa có ảnh / đang tải / lỗi (khi đó hiển thị chữ cái đầu). */
export function useAvatarSrc(memberId?: UUID | null, version?: string | null): string | null {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    if (!memberId || !version) { setSrc(null); return; }
    let alive = true;
    load(memberId, version).then((url) => { if (alive) setSrc(url); });
    return () => { alive = false; };
  }, [memberId, version]);
  return src;
}

export const AVATAR_ACCEPT = "image/jpeg,image/png,image/webp";
export const AVATAR_MAX_BYTES = 5 * 1024 * 1024;

/** Kiểm tra sớm ở trình duyệt cho thông báo nhanh; backend vẫn kiểm tra lại nội dung thật của file. */
export function avatarFileProblem(f: File): string | null {
  if (!AVATAR_ACCEPT.split(",").includes(f.type)) return "Chỉ nhận ảnh JPEG, PNG hoặc WEBP";
  if (f.size > AVATAR_MAX_BYTES) return "Ảnh vượt quá 5MB";
  return null;
}
