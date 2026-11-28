/**
 * Đăng nhập Google / Facebook phía trình duyệt: lấy token từ nhà cung cấp rồi gửi cho backend
 * (POST /auth/social/{provider}); backend tự xác minh token, frontend không tin bất kỳ thông tin nào trong token.
 * - Google: Google Identity Services → ID token (JWT). Nút do Google vẽ (bắt buộc theo quy định thương hiệu).
 * - Facebook: JS SDK → user access token.
 * Script chỉ nạp khi trang có nút đăng nhập; thiếu biến môi trường thì nút bị ẩn, không làm hỏng trang.
 */
export const GOOGLE_CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined)?.trim() || "";
export const FACEBOOK_APP_ID = (import.meta.env.VITE_FACEBOOK_APP_ID as string | undefined)?.trim() || "";
// Phiên bản Graph API mới nhất lúc viết (07/2026). Meta ngừng hỗ trợ mỗi phiên bản sau ~2 năm → nâng định kỳ.
const FACEBOOK_SDK_VERSION = (import.meta.env.VITE_FACEBOOK_SDK_VERSION as string | undefined)?.trim() || "v26.0";

const scripts = new Map<string, Promise<void>>();

function loadScript(src: string): Promise<void> {
  let p = scripts.get(src);
  if (!p) {
    p = new Promise<void>((resolve, reject) => {
      const el = document.createElement("script");
      el.src = src;
      el.async = true;
      el.defer = true;
      el.onload = () => resolve();
      el.onerror = () => {
        scripts.delete(src);                         // lỗi mạng / bị trình chặn quảng cáo chặn → lần sau thử lại
        el.remove();
        reject(new Error("Không tải được dịch vụ đăng nhập. Kiểm tra mạng hoặc tắt trình chặn quảng cáo rồi thử lại."));
      };
      document.head.appendChild(el);
    });
    scripts.set(src, p);
  }
  return p;
}

/* ---------------- Google ---------------- */
interface GoogleId {
  initialize(cfg: { client_id: string; callback: (r: { credential?: string }) => void; ux_mode?: "popup";
                    auto_select?: boolean; cancel_on_tap_outside?: boolean; use_fedcm_for_button?: boolean }): void;
  renderButton(el: HTMLElement, opts: Record<string, unknown>): void;
}
type GoogleWindow = Window & { google?: { accounts: { id: GoogleId } } };

let googleCallback: (idToken: string) => void = () => undefined;
let googleReady: Promise<GoogleId> | null = null;

function google(): Promise<GoogleId> {
  if (!googleReady) {
    googleReady = loadScript("https://accounts.google.com/gsi/client").then(() => {
      const id = (window as GoogleWindow).google!.accounts.id;
      // initialize chỉ gọi MỘT lần cho cả trang (gọi lại nhiều lần Google sẽ cảnh báo); callback được thay theo nút đang hiện
      id.initialize({ client_id: GOOGLE_CLIENT_ID, ux_mode: "popup", auto_select: false, use_fedcm_for_button: true,
                      callback: (r) => { if (r.credential) googleCallback(r.credential); } });
      return id;
    }).catch((e) => { googleReady = null; throw e; });
  }
  return googleReady;
}

export async function renderGoogleButton(el: HTMLElement, onIdToken: (idToken: string) => void,
                                         opts: { dark: boolean; text: "signin_with" | "signup_with" | "continue_with"; width: number }) {
  const id = await google();
  googleCallback = onIdToken;
  el.innerHTML = "";
  id.renderButton(el, {
    type: "standard", size: "large", shape: "rectangular", logo_alignment: "left", locale: "vi",
    theme: opts.dark ? "filled_black" : "outline", text: opts.text, width: Math.round(Math.min(400, opts.width)),
  });
}

/* ---------------- Facebook ---------------- */
interface FacebookSdk {
  init(cfg: { appId: string; version: string; cookie?: boolean; xfbml?: boolean }): void;
  login(cb: (r: { authResponse?: { accessToken: string } | null; status?: string }) => void,
        opts: { scope: string; auth_type?: string }): void;
}
type FbWindow = Window & { FB?: FacebookSdk; fbAsyncInit?: () => void };
let fbReady: Promise<FacebookSdk> | null = null;

function facebook(): Promise<FacebookSdk> {
  if (!fbReady) {
    fbReady = loadScript("https://connect.facebook.net/vi_VN/sdk.js").then(() => {
      const FB = (window as FbWindow).FB!;
      FB.init({ appId: FACEBOOK_APP_ID, version: FACEBOOK_SDK_VERSION, cookie: false, xfbml: false });
      return FB;
    }).catch((e) => { fbReady = null; throw e; });
  }
  return fbReady;
}

/** Nạp SDK sớm (khi trang hiện nút) để lúc bấm, FB.login chạy ngay trong sự kiện click — trình duyệt mới không chặn popup. */
export function preloadFacebook() {
  if (FACEBOOK_APP_ID) facebook().catch(() => undefined);
}

export async function facebookAccessToken(): Promise<string> {
  // Facebook chặn FB.login trên mọi trang http (kể cả localhost) và KHÔNG gọi callback → không chặn ở đây thì nút treo mãi
  if (location.protocol !== "https:") {
    throw new Error("Facebook chỉ cho đăng nhập trên trang HTTPS. Khi phát triển ở máy, chạy `npm run dev:https`.");
  }
  const FB = await facebook();
  return new Promise((resolve, reject) => {
    // Trên Chrome, SDK dùng FedCM (hộp thoại của trình duyệt); vài trường hợp (chặn FedCM, đóng hộp thoại kiểu lạ)
    // SDK không gọi callback → sau 2 phút trả lỗi để nút không treo mãi, người dùng bấm lại được
    const timer = setTimeout(() => reject(new Error("Không nhận được phản hồi từ Facebook. Vui lòng thử lại.")), 120_000);
    FB.login((r) => {
      clearTimeout(timer);
      if (r.authResponse?.accessToken) resolve(r.authResponse.accessToken);
      else reject(new Error("Bạn đã huỷ đăng nhập Facebook."));
    }, { scope: "public_profile,email", auth_type: "rerequest" });   // rerequest: hỏi lại quyền email nếu lần trước bị bỏ chọn
  });
}
