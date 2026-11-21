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
  outfits: { id: number; image: string | null; items: Item[]; rating: number | null; status: string; source: string }[];
  missing: string[]; chosen: boolean;
};
export type SwapOptions = { slot: string; current: Item[]; removable: boolean; options: Item[][] };

export const SLOT_LABEL: Record<string, string> = {
  capospalla: "Cappotto", giacca: "Giacca", strato: "Maglione", top: "Camicia o maglia", sotto: "Pantaloni",
  scarpe: "Scarpe", cravatta: "Cravatta", accessorio: "Accessorio",
};
// Pezzi che si possono aggiungere o togliere senza rompere l'outfit.
export const OPTIONAL_SLOTS: Record<string, string[]> = {
  completo: ["strato", "capospalla"], informale: ["giacca", "strato", "capospalla"], libero: ["giacca", "strato", "capospalla"],
};

export type Garment = {
  id: number; name: string; category: string; category_id: number; slot: string; color_hex: string;
  color_family: string; pattern: string; formality: number; weight: number; material: string | null;
  rain_ok: number; rain_gear: number; set_key: string | null; size: string | null; brand: string | null;
  price_eur: number | null; bought_on: string | null; status: string; city_id: number; photo: string;
  cutout: string | null; notes: string | null; last_worn: string | null; to_review?: number; colors?: { hex: string; share: number }[];
};
export type Category = { id: number; name: string; slot: string; repeat_days: number | null;
  default_formality: number; default_weight: number };
export type City = { id: number; name: string; lat: number; lon: number; country: string; is_home: number };
export type ColorFamily = { name: string; hex: string; tone: string; depth: string };

export const STATUS_LABEL: Record<string, string> = {
  pulito: "Pulito", da_lavare: "Da lavare", tintoria: "In tintoria", valigia: "In valigia", sarta: "Dalla sarta",
};
