import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { FACEBOOK_APP_ID, GOOGLE_CLIENT_ID, facebookAccessToken, preloadFacebook, renderGoogleButton } from "../lib/social";
import { useUI } from "../theme/ThemeProvider";
import s from "./SocialLogin.module.css";

export type SocialProvider = "google" | "facebook";
type Text = "signin_with" | "signup_with" | "continue_with";

const LABEL: Record<Text, (name: string) => string> = {
  signin_with: (n) => `Đăng nhập bằng ${n}`,
  signup_with: (n) => `Đăng ký bằng ${n}`,
  continue_with: (n) => `Tiếp tục với ${n}`,
};

/*
 * Logo đúng màu gốc: quy định thương hiệu của Google không cho đổi màu chữ "G"; Meta chỉ cho logo "f" màu xanh chính
 * thức (hoặc trắng/đen). Phần nút (nền, viền, chữ, hover) dùng skin "secondary" của theme để đồng bộ với hệ thống.
 * Hai logo vẽ inline (lucide-react không có logo thương hiệu đúng chuẩn).
 */
function GoogleLogo() {
  return (
    <svg viewBox="0 0 48 48" width={18} height={18} aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

function FacebookLogo() {
  return (
    <svg viewBox="0 0 24 24" width={20} height={20} aria-hidden>
      <circle cx="12" cy="12" r="11.5" fill="#fff" />
      <path fill="#0866FF" d="M24 12.07C24 5.4 18.63 0 12 0S0 5.4 0 12.07C0 18.1 4.39 23.1 10.13 24v-8.44H7.08v-3.49h3.04V9.41c0-3.02 1.8-4.7 4.54-4.7 1.31 0 2.68.24 2.68.24v2.97h-1.5c-1.5 0-1.96.93-1.96 1.89v2.26h3.33l-.53 3.5h-2.8V24C19.62 23.1 24 18.1 24 12.07z" />
    </svg>
  );
}

/** Hai nút giống hệt nhau: logo cố định ở cột trái, chữ căn giữa, cột phải đối xứng để chữ không lệch. */
function Face({ logo, label, busy }: { logo: ReactNode; label: string; busy: boolean }) {
  return (
    <>
      <span className={s.logo}>{busy ? <Loader2 size={18} className={s.spin} /> : logo}</span>
      <span className={s.label}>{label}</span>
      <span className={s.logo} aria-hidden />
    </>
  );
}

/**
 * Nút đăng nhập Google + Facebook. Không có VITE_GOOGLE_CLIENT_ID / VITE_FACEBOOK_APP_ID thì không hiện gì.
 * onToken nhận token của nhà cung cấp; chỗ gọi gửi nó cho backend (đăng nhập hoặc liên kết).
 */
export function SocialLogin({ onToken, text = "signin_with", divider = true, disabled = false,
                             only = ["google", "facebook"] }: {
  onToken: (provider: SocialProvider, token: string) => Promise<void>;
  text?: Text;
  divider?: boolean;
  disabled?: boolean;
  only?: SocialProvider[];               // vd khi liên kết: chỉ hiện nhà cung cấp chưa liên kết
}) {
  const showGoogle = !!GOOGLE_CLIENT_ID && only.includes("google");
  const showFacebook = !!FACEBOOK_APP_ID && only.includes("facebook");
  const skin = useUI().createButtonSkin("secondary");
  const googleLayer = useRef<HTMLDivElement>(null);
  const wrapEl = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState<SocialProvider | null>(null);
  const [error, setError] = useState<string | null>(null);
  // "loading" → "ready" (có nút Google trong suốt phủ lên) | "failed" (Google không vẽ nút, vd origin chưa khai báo)
  const [google, setGoogle] = useState<"loading" | "ready" | "failed">("loading");
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

  useLayoutEffect(() => {
    const el = wrapEl.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.round(e.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Nút chính thức của Google được vẽ TRONG SUỐT, phủ đúng lên nút của mình: người dùng thấy nút đồng bộ với hệ thống,
  // cú bấm vẫn đi vào nút của Google → nhận ID token như cũ (backend không đổi)
  useEffect(() => {
    if (!showGoogle || !googleLayer.current || width < 120) return;
    renderGoogleButton(googleLayer.current, (idToken) => void run("google", async () => idToken),
                       { dark: false, text, width })
      .then(() => new Promise((r) => setTimeout(r, 1500)))
      .then(() => setGoogle(googleLayer.current?.querySelector("iframe") ? "ready" : "failed"))
      .catch(() => setGoogle("failed"));
  }, [text, width, showGoogle]);

  useEffect(preloadFacebook, []);

  if (!showGoogle && !showFacebook) return null;
  const off = !!busy || disabled;
  return (
    <div ref={wrapEl} className={s.wrap} aria-busy={!!busy}>
      {divider && <div className={s.divider}><span>hoặc</span></div>}
      {error && <div className={s.error} role="alert">{error}</div>}
      <div className={`${s.buttons} ${off ? s.dim : ""}`}>
        {showGoogle && (
          <div className={s.googleWrap}>
            {/* Nút nhìn thấy. Bình thường cú bấm đi vào nút Google trong suốt phía trên; nếu Google không vẽ được nút
                thì chính nút này nhận click và báo lý do, thay vì bấm không có phản hồi */}
            <button type="button" className={s.btn} style={skin}
                    tabIndex={google === "ready" ? -1 : 0} aria-hidden={google === "ready"}
                    onClick={() => google === "failed" && setError(
                      "Không mở được đăng nhập Google trên trang này. Có thể địa chỉ trang chưa được khai báo trong "
                      + "Google Cloud (Authorized JavaScript origins), hoặc trình chặn quảng cáo đang chặn Google.")}>
              <Face logo={<GoogleLogo />} label={LABEL[text]("Google")} busy={busy === "google"} />
            </button>
            <div ref={googleLayer} className={s.googleLayer} />
          </div>
        )}
        {showFacebook && (
          <button type="button" className={s.btn} style={skin} disabled={off}
                  onClick={() => void run("facebook", facebookAccessToken)}>
            <Face logo={<FacebookLogo />} label={busy === "facebook" ? "Đang kết nối Facebook…" : LABEL[text]("Facebook")}
                  busy={busy === "facebook"} />
          </button>
        )}
      </div>
    </div>
  );
}
