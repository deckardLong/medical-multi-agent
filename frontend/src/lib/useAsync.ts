import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";

/** Tải dữ liệu theo deps; bỏ qua kết quả của lần gọi cũ (vd đổi thành viên khi request trước chưa về). */
export function useAsync<T>(fn: () => Promise<T>, deps: DependencyList) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);

  const reload = useCallback(async () => {
    const my = ++seq.current;
    setLoading(true);
    try {
      const result = await run();
      if (my === seq.current) { setData(result); setError(null); }
    } catch (e) {
      if (my === seq.current) setError((e as Error).message);
    } finally {
      if (my === seq.current) setLoading(false);
    }
  }, [run]);

  useEffect(() => { reload(); }, [reload]);

  return { data, error, loading, reload, setData };
}
