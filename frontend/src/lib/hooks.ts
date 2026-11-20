import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

/** Carica un indirizzo dell'API e lo ricarica a richiesta. */
export function useApi<T>(url: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async () => {
    if (!url) return;
    setLoading(true);
    setError("");
    try {
      setData(await api.get<T>(url));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => { reload(); }, [reload]);
  return { data, error, loading, reload, setData };
}
