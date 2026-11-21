import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { enablePush, isIos, isStandalone } from "@/lib/push";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, PageTitle, inputCls } from "@/components/Section";

type S = { notify_time: string; trip_alert_days: number; the361_url: string; home_city_id: number; timezone: string };
type Status = { calendar: { ok?: boolean; message?: string; at?: string }; mail: boolean; push: boolean; photos: string;
  last_evening: string | null; log: { id: number; sent_at: string; kind: string; title: string }[] };
type Cal = { weeks: { week_start: string; week_type: string }[]; labels: Record<string, string> };
const DAYS = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"];

export default function Settings() {
  const { data } = useApi<S>("/settings");
  const { data: st, reload } = useApi<Status>("/status");
  const { data: cal, reload: reloadCal } = useApi<Cal>("/calendar");
  const { data: rules, reload: reloadRules } = useApi<{ week_type: string; weekday: number; dress_code: string }[]>("/dress-rules");
  const [f, setF] = useState<S | null>(null);
  const [msg, setMsg] = useState("");
  useEffect(() => { if (data) setF(data); }, [data]);
  if (!f) return null;

  async function act(label: string, fn: () => Promise<unknown>) {
    setMsg(label + "…");
    try { await fn(); setMsg(label + ": fatto."); } catch (e) { setMsg(`${label}: ${(e as Error).message}`); }
    reload();
  }

  const today = new Date().toISOString().slice(0, 10);
  const weekTypes = Array.from(new Set(rules?.map((r) => r.week_type)));

  return (
    <div className="space-y-4">
      <PageTitle title="Impostazioni" back />
      <Card><CardContent className="space-y-3 pt-4">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Ora della mail serale"><input type="time" className={inputCls} value={f.notify_time} onChange={(e) => setF({ ...f, notify_time: e.target.value })} /></Field>
          <Field label="Avviso viaggi (giorni prima)"><input type="number" min={1} max={7} className={inputCls} value={f.trip_alert_days} onChange={(e) => setF({ ...f, trip_alert_days: Number(e.target.value) })} /></Field>
        </div>
        <Field label="Calendario the361 (JSON)"><input className={inputCls} value={f.the361_url} onChange={(e) => setF({ ...f, the361_url: e.target.value })} /></Field>
        <p className="text-xs text-muted-foreground">La mail parte tra le 18 e le 21:45 (ora di Bruxelles): fuori da questa fascia il cron non passa.</p>
        <Button onClick={() => act("Salvo", () => api.put("/settings", f))}>Salva</Button>
      </CardContent></Card>

      <Card><CardContent className="space-y-2 pt-4 text-sm">
        <p className="font-medium">Avvisi e fonti</p>
        <p>Mail: {st?.mail ? "attiva" : "non configurata (manca la chiave Resend)"}</p>
        <p>Calendario the361: {st?.calendar.ok === false ? st.calendar.message : st?.calendar.ok ? "ok" : "mai aggiornato"}{st?.calendar.at ? ` (${st.calendar.at})` : ""}</p>
        <p>Foto: {st?.photos}</p>
        <p>Ultima mail serale: {st?.last_evening ?? "mai"}</p>
        <div className="flex flex-wrap gap-2 pt-1">
          <Button size="sm" variant="outline" onClick={() => act("Mail di prova", () => api.post("/notify/test"))}>Mail di prova</Button>
          <Button size="sm" variant="outline" onClick={() => act("Mail della sera", () => api.post("/notify/evening-now"))}>Manda ora la mail della sera</Button>
          <Button size="sm" variant="outline" onClick={() => act("Calendario", () => api.post("/calendar/refresh"))}>Aggiorna calendario</Button>
          {st?.push && <Button size="sm" variant="outline" onClick={() => act("Notifiche push", enablePush)}>Attiva le notifiche push</Button>}
        </div>
        {st?.push && isIos() && !isStandalone() && (
          <p className="rounded-md bg-muted p-2 text-xs">Su iPhone le notifiche push funzionano solo dall'app sulla schermata Home: tocca Condividi, poi “Aggiungi alla schermata Home”, e apri Style.me da lì.</p>
        )}
        {msg && <p className="text-muted-foreground">{msg}</p>}
      </CardContent></Card>

      <Card><CardContent className="space-y-2 pt-4 text-sm">
        <p className="font-medium">Dress code per tipo di settimana</p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead><tr><th />{DAYS.map((d) => <th key={d} className="px-1 font-normal text-muted-foreground">{d}</th>)}</tr></thead>
            <tbody>
              {weekTypes.map((wt) => (
                <tr key={wt}>
                  <td className="pr-2">{cal?.labels[wt] ?? wt}</td>
                  {DAYS.map((_, i) => {
                    const r = rules?.find((x) => x.week_type === wt && x.weekday === i);
                    return (
                      <td key={i} className="px-0.5">
                        <select className="rounded border border-border bg-transparent" value={r?.dress_code ?? ""}
                          onChange={async (e) => { await api.put("/dress-rules", { week_type: wt, weekday: i, dress_code: e.target.value }); reloadRules(); }}>
                          <option value="completo">C</option><option value="informale">I</option><option value="libero">L</option>
                        </select>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted-foreground">C completo, I informale, L libero.</p>
      </CardContent></Card>

      <Card><CardContent className="space-y-2 pt-4 text-sm">
        <p className="font-medium">Calendario PE (prossime settimane)</p>
        {cal?.weeks.filter((w) => w.week_start >= today.slice(0, 8) + "01").slice(0, 12).map((w) => (
          <div key={w.week_start} className="flex items-center justify-between">
            <span>{new Date(w.week_start + "T12:00:00").toLocaleDateString("it-IT", { day: "numeric", month: "short" })}</span>
            <select className="rounded border border-border bg-transparent" value={w.week_type}
              onChange={async (e) => { await api.put(`/calendar/${w.week_start}`, { week_type: e.target.value }); reloadCal(); }}>
              {Object.entries(cal.labels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
        ))}
        <p className="text-xs text-muted-foreground">Le settimane non elencate contano come settimane di commissione.</p>
      </CardContent></Card>

      <Button variant="ghost" className="w-full" onClick={async () => { await api.post("/auth/logout"); location.href = "/login"; }}>Esci</Button>
    </div>
  );
}
