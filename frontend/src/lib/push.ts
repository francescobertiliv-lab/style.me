import { api } from "./api";

export const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent);
export const isStandalone = () =>
  window.matchMedia("(display-mode: standalone)").matches || (navigator as unknown as { standalone?: boolean }).standalone === true;

function urlB64ToUint8Array(base64: string) {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export async function enablePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    throw new Error(isIos() ? "aggiungi prima Style.me alla schermata Home" : "questo browser non supporta le notifiche push");
  }
  const perm = await Notification.requestPermission();
  if (perm !== "granted") throw new Error("permesso negato");
  const { key } = await api.get<{ key: string }>("/push/key");
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlB64ToUint8Array(key) });
  await api.post("/push/subscribe", { ...sub.toJSON(), device: isIos() ? "iPhone" : navigator.platform });
}
