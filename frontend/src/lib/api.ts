// Tutte le chiamate al backend passano da qui. Il cookie di sessione viaggia da solo.
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  const isForm = body instanceof FormData;
  const res = await fetch(`/api${url}`, {
    method,
    credentials: "include",
    headers: body && !isForm ? { "Content-Type": "application/json" } : undefined,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });
  if (res.status === 401 && !url.startsWith("/auth")) {
    window.location.href = "/login";
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      msg = (await res.json()).detail ?? msg;
    } catch { /* risposta senza JSON */ }
    throw new ApiError(res.status, msg);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  get: <T,>(url: string) => request<T>("GET", url),
  post: <T,>(url: string, body?: unknown) => request<T>("POST", url, body),
  patch: <T,>(url: string, body?: unknown) => request<T>("PATCH", url, body),
  put: <T,>(url: string, body?: unknown) => request<T>("PUT", url, body),
  del: <T,>(url: string) => request<T>("DELETE", url),
};

export type Item = {
  id: number; name: string; category: string; slot: string; color_hex: string;
  color_family: string; pattern: string; cutout: string | null; photo: string; formality: number;
};
export type DayPlan = {
  date: string; week_label: string; dress_code: "completo" | "informale" | "libero";
  reason: string; overridden: boolean; city: string; weather_text: string; weather_ok: boolean;
  calendar_ok: boolean; trip: { id: number; destination: string } | null;
  outfits: { id: number; image: string | null; items: Item[]; rating: number | null; status: string }[];
  missing: string[];
};
