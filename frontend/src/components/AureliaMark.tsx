import { useId } from "react";

/**
 * Linh vật AURELIA (sứa mặt trăng) bản rút gọn cho kích thước nhỏ — bản đầy đủ: docs/assets/aurelia-logo.svg.
 * 4 vòng tròn xếp thành dấu cộng y tế; 3 xúc tu = 3 lần đọc ảnh song song.
 * mono: vẽ bằng currentColor (dùng trên nền gradient, nơi gradient của logo sẽ chìm mất).
 */
export function AureliaMark({ size = 28, mono = false }: { size?: number; mono?: boolean }) {
  const id = useId();                       // mỗi logo một id gradient → không đụng nhau khi trang có nhiều logo
  const stroke = mono ? "currentColor" : `url(#${id})`;
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden
         strokeLinecap="round" strokeLinejoin="round">
      {!mono && (
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#3DB4FE" />
            <stop offset="1" stopColor="#4CECB8" />
          </linearGradient>
        </defs>
      )}
      <path d="M8 31 C8 9 56 9 56 31 C52 34 48 34 44 31.5 C40 34 36 34 32 31.5 C28 34 24 34 20 31.5 C16 34 12 34 8 31 Z"
            stroke={stroke} strokeWidth="3.4" fill={mono ? "none" : `url(#${id})`} fillOpacity={0.16} />
      <g stroke={mono ? "currentColor" : "#4CECB8"} strokeWidth="2.6">
        <circle cx="32" cy="15.5" r="3.6" />
        <circle cx="38.5" cy="21.5" r="3.6" />
        <circle cx="32" cy="27.5" r="3.6" />
        <circle cx="25.5" cy="21.5" r="3.6" />
      </g>
      <g stroke={stroke} strokeWidth="3.4">
        <path d="M22 37 C19 44 25 48 21 56" />
        <path d="M32 38 C29 45 35 50 31 60" />
        <path d="M42 37 C45 44 39 48 43 56" />
      </g>
    </svg>
  );
}
