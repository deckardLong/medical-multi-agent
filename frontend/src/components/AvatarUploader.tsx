import { useRef, useState } from "react";
import { Camera, Loader2, Trash2 } from "lucide-react";
import { avatars } from "../api/endpoints";
import type { UUID } from "../api/types";
import { AVATAR_ACCEPT, avatarFileProblem } from "../lib/avatar";
import { useToast } from "../state/ToastContext";
import { Avatar } from "./ui";
import s from "./AvatarUploader.module.css";

/**
 * Avatar kèm nút đổi ảnh. Quyền do backend quyết (thành viên tự quản lý hồ sơ → 404): chỗ gọi chỉ hiển thị
 * component này khi người dùng có quyền ghi, chỗ khác dùng <Avatar> thường.
 */
export function AvatarUploader({ memberId, name, version, size = 64, onChanged }: {
  memberId: UUID; name: string; version: string | null; size?: number; onChanged: () => unknown;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function run(action: () => Promise<unknown>, ok: string) {
    setBusy(true);
    try {
      await action();
      await onChanged();
      toast.success(ok);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function pick(f: File | undefined) {
    if (input.current) input.current.value = "";        // chọn lại cùng một file vẫn kích hoạt onChange
    if (!f) return;
    const problem = avatarFileProblem(f);
    if (problem) { toast.error(problem); return; }
    void run(() => avatars.upload(memberId, f), `Đã cập nhật ảnh đại diện của ${name}`);
  }

  const btn = Math.max(24, Math.round(size * 0.36));
  return (
    <div className={s.wrap} style={{ width: size, height: size }}>
      <Avatar name={name} size={size} memberId={memberId} version={version} />
      {busy && <span className={s.busy}><Loader2 size={size * 0.34} className={s.spin} /></span>}
      <button type="button" className={s.cam} style={{ width: btn, height: btn }} disabled={busy}
              onClick={() => input.current?.click()} title="Đổi ảnh đại diện" aria-label={`Đổi ảnh đại diện của ${name}`}>
        <Camera size={btn * 0.55} />
      </button>
      {version && !busy && (
        <button type="button" className={s.remove} style={{ width: btn * 0.82, height: btn * 0.82 }}
                onClick={() => void run(() => avatars.remove(memberId), `Đã xoá ảnh đại diện của ${name}`)}
                title="Xoá ảnh đại diện" aria-label={`Xoá ảnh đại diện của ${name}`}>
          <Trash2 size={btn * 0.42} />
        </button>
      )}
      <input ref={input} type="file" accept={AVATAR_ACCEPT} hidden onChange={(e) => pick(e.target.files?.[0])} />
    </div>
  );
}
