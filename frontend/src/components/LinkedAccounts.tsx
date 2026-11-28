import { CheckCircle2 } from "lucide-react";
import { auth } from "../api/endpoints";
import { useAsync } from "../lib/useAsync";
import { FACEBOOK_APP_ID, GOOGLE_CLIENT_ID } from "../lib/social";
import { useToast } from "../state/ToastContext";
import { SocialLogin, type SocialProvider } from "./SocialLogin";
import s from "./SocialLogin.module.css";

const LABEL: Record<SocialProvider, string> = { google: "Google", facebook: "Facebook" };

/**
 * Liên kết Google/Facebook với tài khoản đang đăng nhập. Cần cho trường hợp email đã có tài khoản mật khẩu:
 * backend không tự gộp khi nhà cung cấp không xác minh email (Facebook) và trả 409 "hãy liên kết trong phần cài đặt".
 */
export function LinkedAccounts() {
  const toast = useToast();
  const linked = useAsync(() => auth.linkedAccounts(), []);
  const providers = ([GOOGLE_CLIENT_ID && "google", FACEBOOK_APP_ID && "facebook"].filter(Boolean)) as SocialProvider[];
  if (!providers.length) return null;
  const done = new Map((linked.data ?? []).map((a) => [a.provider, a.email]));
  const missing = providers.filter((p) => !done.has(p));

  return (
    <div style={{ padding: "4px 10px 10px", display: "grid", gap: 8, width: 320, boxSizing: "border-box" }}>
      <div className="muted" style={{ fontSize: 12 }}>Tài khoản liên kết</div>
      {providers.filter((p) => done.has(p)).map((p) => (
        <div key={p} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <CheckCircle2 size={15} color="var(--c-success)" aria-hidden />
          <span><strong>{LABEL[p]}</strong>{done.get(p) ? <span className="muted"> · {done.get(p)}</span> : null}</span>
        </div>
      ))}
      {linked.data && missing.length > 0 && (
        <div className={s.linkBox}>
          <SocialLogin divider={false} text="continue_with" only={missing} onToken={async (provider, token) => {
            await auth.link(provider, token);
            toast.success(`Đã liên kết ${LABEL[provider]}. Lần sau có thể đăng nhập bằng ${LABEL[provider]}.`);
            await linked.reload();
          }} />
        </div>
      )}
    </div>
  );
}
