import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { family as familyApi } from "../api/endpoints";
import type { Family, FamilyMember, UUID } from "../api/types";

const SELECTED_KEY = "fh.member";

interface MemberCtx {
  family: Family | null;
  members: FamilyMember[];
  current: FamilyMember | null;        // thành viên đang được chat/xem lịch/xem hồ sơ
  select: (id: UUID) => void;
  reload: () => Promise<void>;
  loading: boolean;
}

const Ctx = createContext<MemberCtx | null>(null);

export function MemberProvider({ children }: { children: ReactNode }) {
  const [family, setFamily] = useState<Family | null>(null);
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [selected, setSelected] = useState<UUID | null>(() => {
    try { return localStorage.getItem(SELECTED_KEY); } catch { return null; }
  });
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    const [f, ms] = await Promise.all([familyApi.mine(), familyApi.members()]);
    setFamily(f);
    setMembers(ms);
    setLoading(false);
  }, []);

  useEffect(() => {
    reload().catch(() => setLoading(false));
  }, [reload]);

  const select = useCallback((id: UUID) => {
    setSelected(id);
    try { localStorage.setItem(SELECTED_KEY, id); } catch { /* bỏ qua */ }
  }, []);

  // Thành viên đã chọn có thể không còn (đổi tài khoản) → rơi về "chính tôi"
  const current = members.find((m) => m.id === selected) ?? members.find((m) => m.member_type === "self") ?? members[0] ?? null;

  const value = useMemo(() => ({ family, members, current, select, reload, loading }),
    [family, members, current, select, reload, loading]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useMembers(): MemberCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useMembers phải nằm trong <MemberProvider>");
  return ctx;
}
