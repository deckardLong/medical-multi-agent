import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Facebook } from "lucide-react";
import { FACEBOOK_APP_ID, GOOGLE_CLIENT_ID, facebookAccessToken, preloadFacebook, renderGoogleButton } from "../lib/social";
import { useTheme } from "../theme/ThemeProvider";
import s from "./SocialLogin.module.css";

export type SocialProvider = "google" | "facebook";

/**
 * Nút đăng nhập Google + Facebook. Không có VITE_GOOGLE_CLIENT_ID / VITE_FACEBOOK_APP_ID thì không hiện gì.
 * onToken nhận token của nhà cung cấp; chỗ gọi gửi nó cho backend (đăng nhập hoặc liên kết).
 */
export function SocialLogin({ onToken, text = "signin_with", divider = true, disabled = false,
                             only = ["google", "facebook"] }: {
  onToken: (provider: SocialProvider, token: string) => Promise<void>;
  text?: "signin_with" | "signup_with" | "continue_with";
  divider?: boolean;
  disabled?: boolean;
  only?: SocialProvider[];               // vd khi liên kết: chỉ hiện nhà cung cấp chưa liên kết
}) {
  const showGoogle = !!GOOGLE_CLIENT_ID && only.includes("google");
  const showFacebook = !!FACEBOOK_APP_ID && only.includes("facebook");
  const { name } = useTheme();
  const googleEl = useRef<HTMLDivElement>(null);
  const wrapEl = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState<SocialProvider | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [width, setWidth] = useState(0);
  const latest = useRef(onToken);
  latest.current = onToken;

  async function run(provider: SocialProvider, getToken: () => Promise<string>) {
    setError(null);
    setBusy(provider);
    try {
      await latest.current(provider, await getToken());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  // Nút Google có bề rộng cố định (px) do Google vẽ → đo khung NGOÀI (không bị nút kéo giãn), vẽ lại khi đổi kích thước
  useLayoutEffect(() => {
    const el = wrapEl.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.round(e.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!showGoogle || !googleEl.current || width < 120) return;
    renderGoogleButton(googleEl.current, (idToken) => void run("google", async () => idToken),
                       { dark: name === "dark", text, width })
      .catch((e) => setError((e as Error).message));
  }, [name, text, width, showGoogle]);     // vẽ lại theo theme sáng/tối

  useEffect(preloadFacebook, []);

  if (!showGoogle && !showFacebook) return null;
  return (
    <div ref={wrapEl} className={s.wrap} aria-busy={!!busy}>
      {divider && <div className={s.divider}><span>hoặc</span></div>}
      {error && <div className={s.error} role="alert">{error}</div>}
      <div className={`${s.buttons} ${busy || disabled ? s.dim : ""}`}>
        {showGoogle && <div className={s.google}><div ref={googleEl} /></div>}
        {showFacebook && (
          <button type="button" className={s.facebook} disabled={!!busy || disabled}
                  onClick={() => void run("facebook", facebookAccessToken)}>
            <Facebook size={18} fill="currentColor" strokeWidth={0} aria-hidden />
            {busy === "facebook" ? "Đang kết nối Facebook…" : {
              signin_with: "Đăng nhập bằng Facebook", signup_with: "Đăng ký bằng Facebook",
              continue_with: "Tiếp tục với Facebook" }[text]}
          </button>
        )}
      </div>
      {busy === "google" && <p className={s.note}>Đang đăng nhập bằng Google…</p>}
    </div>
  );
}
