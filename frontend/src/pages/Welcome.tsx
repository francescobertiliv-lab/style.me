import { useEffect, useState } from "react";
import { Camera, Check, Share } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, type Category, type City, type Garment } from "@/lib/api";
import { enablePush, isIos, isStandalone } from "@/lib/push";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, inputCls } from "@/components/Section";

type Step = "password" | "casa" | "mail" | "iphone" | "misure" | "capi";
type Me = { logged_in: boolean; needs_setup: boolean; onboarded: boolean };

/** Primo avvio: sei passi brevi, ognuno si può rifare dopo dalle impostazioni. */
export default function Welcome() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);

  const [saved, setSaved] = useState<Step | null>(null);
  useEffect(() => {
    api.get<Me>("/auth/me").then(async (m) => {
      if (!m.needs_setup && !m.logged_in) return navigate("/login", { replace: true });
      // Riparto dal passo dove ero arrivato, anche se apro l'app da un altro dispositivo.
      if (m.logged_in) {
        const s = await api.get<{ onboarding_step: Step | null }>("/settings").catch(() => null);
        setSaved(s?.onboarding_step ?? null);
      }
      setMe(m);
    });
  }, [navigate]);

  if (!me) return null;
  const steps: Step[] = [...(me.needs_setup ? ["password" as const] : []), "casa", "mail", "iphone", "misure", "capi"];
  const asked = (params.get("passo") as Step | null) ?? saved;
  const step: Step = me.needs_setup ? "password" : asked && steps.includes(asked) ? asked : steps[0];
  const idx = steps.indexOf(step);

  function next() {
    if (step === "password") {
      setMe({ ...me!, needs_setup: false, logged_in: true });
      api.put("/settings", { onboarding_step: "casa" }).catch(() => undefined);
      setParams({ passo: "casa" });
      return;
    }
    const n = steps[idx + 1];
    if (n) {
      api.put("/settings", { onboarding_step: n }).catch(() => undefined);
      setParams({ passo: n });
    }
  }

  async function finish() {
    await api.put("/settings", { onboarded: true });
    window.location.replace("/");
  }

  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col px-4 pt-[max(env(safe-area-inset-top),1.5rem)] pb-10">
      <div className="mb-6 space-y-2">
        <p className="text-lg font-semibold tracking-tight">Style.me</p>
        <div className="flex gap-1">
          {steps.map((s, i) => (
            <span key={s} className={cn("h-1 flex-1 rounded-full", i <= idx ? "bg-primary" : "bg-muted")} />
          ))}
        </div>
        <p className="text-xs text-muted-foreground">Passo {idx + 1} di {steps.length}</p>
      </div>
      {step === "password" && <PasswordStep onDone={next} />}
      {step === "casa" && <HomeStep onDone={next} />}
      {step === "mail" && <MailStep onDone={next} />}
      {step === "iphone" && <PhoneStep onDone={next} />}
      {step === "misure" && <SizesStep onDone={next} />}
      {step === "capi" && <GarmentsStep onDone={finish} />}
    </div>
  );
}

function Intro({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4 space-y-2">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <div className="space-y-2 text-sm text-muted-foreground">{children}</div>
    </div>
  );
}

function Skip({ onClick }: { onClick: () => void }) {
  return <button onClick={onClick} className="mt-3 w-full text-center text-sm text-muted-foreground underline">Lo faccio dopo</button>;
}

function PasswordStep({ onDone }: { onDone: () => void }) {
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [error, setError] = useState("");

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (a.length < 8) return setError("Almeno 8 caratteri.");
    if (a !== b) return setError("Le due password non sono uguali.");
    try {
      await api.post("/auth/setup", { password: a });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form onSubmit={save}>
      <Intro title="Benvenuto">
        <p>Style.me ogni sera ti dice cosa mettere domani, prepara la valigia per Strasburgo e tiene il conto di quello che hai.</p>
        <p>Prima cosa: scegli la password. La usi solo tu, l'app non ha altri utenti.</p>
      </Intro>
      <div className="space-y-3">
        <input type="password" autoComplete="new-password" placeholder="Password (almeno 8 caratteri)" className={inputCls}
          value={a} onChange={(e) => setA(e.target.value)} />
        <input type="password" autoComplete="new-password" placeholder="Ripetila" className={inputCls}
          value={b} onChange={(e) => setB(e.target.value)} />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full">Avanti</Button>
      </div>
    </form>
  );
}

type Settings = { home_city_id: number; notify_time: string; trip_alert_days: number; mail_to: string | null; email_from: string | null };

function HomeStep({ onDone }: { onDone: () => void }) {
  const [cities, setCities] = useState<City[]>([]);
  const [s, setS] = useState<Settings | null>(null);
  useEffect(() => {
    api.get<City[]>("/cities").then(setCities);
    api.get<Settings>("/settings").then(setS);
  }, []);
  if (!s) return null;

  async function save() {
    await api.put("/settings", { home_city_id: s!.home_city_id, notify_time: s!.notify_time, trip_alert_days: s!.trip_alert_days });
    onDone();
  }

  return (
    <div>
      <Intro title="Dove sei di solito">
        <p>Serve per il meteo e per sapere quali capi hai sotto mano. Quelli che lasci in Italia li segni con la città giusta.</p>
      </Intro>
      <div className="space-y-4">
        <div className="space-y-2">
          {cities.map((c) => (
            <button key={c.id} onClick={() => setS({ ...s, home_city_id: c.id })}
              className={cn("flex w-full items-center rounded-lg border p-3 text-left text-sm",
                s.home_city_id === c.id ? "border-primary bg-primary/5 font-medium" : "border-border")}>
              <span className="flex-1">{c.name}</span>
              {s.home_city_id === c.id && <Check className="h-4 w-4 text-primary" />}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Mail della sera alle">
            <input type="time" className={inputCls} value={s.notify_time} onChange={(e) => setS({ ...s, notify_time: e.target.value })} />
          </Field>
          <Field label="Avviso viaggi, giorni prima">
            <input type="number" min={1} max={7} className={inputCls} value={s.trip_alert_days}
              onChange={(e) => setS({ ...s, trip_alert_days: Number(e.target.value) })} />
          </Field>
        </div>
        <p className="text-xs text-muted-foreground">Il tipo di giornata (completo o informale) lo prendo dal calendario di the361: plenaria, commissione, settimana verde.</p>
        <Button className="w-full" onClick={save}>Avanti</Button>
      </div>
    </div>
  );
}

function MailStep({ onDone }: { onDone: () => void }) {
  const [s, setS] = useState<Settings | null>(null);
  const [hasKey, setHasKey] = useState(false);
  const [key, setKey] = useState("");
  const [msg, setMsg] = useState("");
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Settings>("/settings").then((x) => setS({ ...x, email_from: x.email_from || "Style.me <onboarding@resend.dev>" }));
    api.get<{ mail: boolean }>("/status").then((st) => setHasKey(st.mail));
  }, []);
  if (!s) return null;

  async function test() {
    setBusy(true);
    setMsg("Salvo e mando la prova…");
    try {
      await api.put("/settings", { mail_to: s!.mail_to, email_from: s!.email_from });
      if (key.trim()) await api.put("/settings/resend-key", { key });
      const r = await api.post<{ email: boolean; email_error?: string }>("/notify/test");
      if (r.email) {
        setOk(true);
        setHasKey(true);
        setMsg("Mail partita. Controlla la posta (anche lo spam), poi vai avanti.");
      } else {
        setMsg(r.email_error ? `Resend ha risposto: ${r.email_error}` : "Manca qualcosa: indirizzo, mittente o chiave.");
      }
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <Intro title="La mail della sera">
        <p>Ogni sera ti arriva una mail con l'outfit di domani e, quando serve, l'avviso per la valigia. Arriva anche se non apri l'app.</p>
        <p>A spedirla è Resend, lo stesso servizio di LAURUS. Puoi usare la stessa chiave: la trovi su resend.com, alla voce API Keys.</p>
      </Intro>
      <div className="space-y-3">
        <Field label="La tua mail">
          <input type="email" className={inputCls} value={s.mail_to ?? ""} onChange={(e) => setS({ ...s, mail_to: e.target.value })} />
        </Field>
        <Field label="Mittente">
          <input className={inputCls} value={s.email_from ?? ""} onChange={(e) => setS({ ...s, email_from: e.target.value })} />
        </Field>
        <p className="text-xs text-muted-foreground">
          Con onboarding@resend.dev la mail arriva solo all'indirizzo con cui sei iscritto a Resend. Se in LAURUS mandi da un tuo dominio, scrivi lo stesso mittente qui.
        </p>
        <Field label={hasKey ? "Chiave Resend (già salvata: scrivila solo per cambiarla)" : "Chiave Resend"}>
          <input type="password" autoComplete="off" placeholder="re_…" className={inputCls} value={key} onChange={(e) => setKey(e.target.value)} />
        </Field>
        <p className="text-xs text-muted-foreground">La chiave resta nel database dell'app e non viene mai mostrata.</p>
        {msg && <p className={cn("text-sm", ok ? "text-primary" : "text-muted-foreground")}>{msg}</p>}
        <Button className="w-full" variant={ok ? "outline" : "default"} disabled={busy} onClick={test}>Salva e mandami una prova</Button>
        {ok && <Button className="w-full" onClick={onDone}>Avanti</Button>}
      </div>
      {!ok && <Skip onClick={onDone} />}
    </div>
  );
}

function PhoneStep({ onDone }: { onDone: () => void }) {
  const [push, setPush] = useState(false);
  const [msg, setMsg] = useState("");
  useEffect(() => { api.get<{ push: boolean }>("/status").then((st) => setPush(st.push)); }, []);
  const installed = isStandalone();

  return (
    <div>
      <Intro title="Mettila sul telefono">
        <p>Così Style.me si apre come un'app, a schermo intero, senza barra del browser.</p>
      </Intro>
      {installed ? (
        <p className="mb-4 flex items-center gap-2 text-sm"><Check className="h-4 w-4 text-primary" /> Fatto: la stai già usando dalla schermata Home.</p>
      ) : (
        <Card className="mb-4"><CardContent className="space-y-2 pt-4 text-sm">
          <p>Su iPhone, da Safari:</p>
          <ol className="list-decimal space-y-1 pl-5">
            <li>tocca <Share className="inline h-4 w-4" /> Condividi, in basso;</li>
            <li>scorri e tocca “Aggiungi alla schermata Home”;</li>
            <li>tocca “Aggiungi”, poi apri Style.me dall'icona.</li>
          </ol>
          {!isIos() && <p className="text-xs text-muted-foreground">Se sei sul computer, fallo quando apri il link dal telefono.</p>}
        </CardContent></Card>
      )}
      {push && (
        <div className="mb-4 space-y-2">
          <p className="text-sm text-muted-foreground">In più, se vuoi, una notifica sul telefono oltre alla mail.</p>
          <Button variant="outline" className="w-full" onClick={() => enablePush().then(() => setMsg("Notifiche attive.")).catch((e) => setMsg(e.message))}>
            Attiva le notifiche
          </Button>
          {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
        </div>
      )}
      <Button className="w-full" onClick={onDone}>Avanti</Button>
    </div>
  );
}

type Prof = { height_cm: number | null; build: string | null; coloring: string | null; sizes: Record<string, string>;
  fit_notes: string | null; budget_min: number | null; budget_max: number | null };
const SIZES = [["camicia", "Camicia (collo)"], ["giacca", "Giacca"], ["pantalone", "Pantalone"], ["scarpe", "Scarpe"], ["maglia", "Maglia"]];

function SizesStep({ onDone }: { onDone: () => void }) {
  const [p, setP] = useState<Prof | null>(null);
  useEffect(() => { api.get<Prof>("/profile").then(setP); }, []);
  if (!p) return null;
  const size = (k: string, v: string) => setP({ ...p, sizes: { ...p.sizes, [k]: v } });

  async function save() {
    await api.put("/profile", p);
    onDone();
  }

  return (
    <div>
      <Intro title="Taglie e budget">
        <p>Servono per i consigli d'acquisto: niente proposte fuori taglia o fuori budget. Il resto del profilo (colori, regole di stile) è già impostato e lo trovi in Stile.</p>
      </Intro>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          {SIZES.map(([k, label]) => (
            <Field key={k} label={label}>
              <input className={inputCls} value={p.sizes[k] ?? ""} onChange={(e) => size(k, e.target.value)} />
            </Field>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Budget per capo, da (€)">
            <input type="number" className={inputCls} value={p.budget_min ?? ""} onChange={(e) => setP({ ...p, budget_min: e.target.value ? Number(e.target.value) : null })} />
          </Field>
          <Field label="a (€)">
            <input type="number" className={inputCls} value={p.budget_max ?? ""} onChange={(e) => setP({ ...p, budget_max: e.target.value ? Number(e.target.value) : null })} />
          </Field>
        </div>
        <Button className="w-full" onClick={save}>Avanti</Button>
      </div>
      <Skip onClick={onDone} />
    </div>
  );
}

type Need = { label: string; hint: string; cats: string[]; count: number; suit?: boolean };
const NEEDS: Need[] = [
  { label: "Completo", hint: "giacca e pantalone, una foto ciascuno", cats: ["giacca completo", "pantalone completo"], count: 2, suit: true },
  { label: "Camicie", hint: "almeno due", cats: ["camicia"], count: 2 },
  { label: "Cravatta", hint: "almeno una", cats: ["cravatta"], count: 1 },
  { label: "Scarpe formali", hint: "un paio", cats: ["scarpe formali"], count: 1 },
  { label: "Polo o t-shirt", hint: "due, per i giorni informali", cats: ["polo", "t-shirt"], count: 2 },
  { label: "Chino o jeans", hint: "un paio", cats: ["chino", "jeans", "pantalone"], count: 1 },
  { label: "Scarpe informali", hint: "sneakers o mocassini", cats: ["sneakers", "mocassini", "stivaletti"], count: 1 },
];

function GarmentsStep({ onDone }: { onDone: () => void }) {
  const navigate = useNavigate();
  const [garments, setGarments] = useState<Garment[] | null>(null);
  const [cats, setCats] = useState<Category[]>([]);
  useEffect(() => {
    api.get<Garment[]>("/garments").then(setGarments);
    api.get<Category[]>("/categories").then(setCats);
  }, []);
  if (!garments) return null;

  const have = (n: Need) => garments.filter((g) => n.cats.includes(g.category)).length;
  // Per il completo conta la coppia: la stessa etichetta su giacca e pantalone.
  const suitDone = (() => {
    const j = garments.filter((g) => g.category === "giacca completo" && g.set_key).map((g) => g.set_key);
    return garments.some((g) => g.category === "pantalone completo" && j.includes(g.set_key));
  })();
  const done = (n: Need) => (n.suit ? suitDone : have(n) >= n.count);
  const total = NEEDS.filter(done).length;

  function shoot(n: Need) {
    // Per il completo: prima la giacca, poi il pantalone, con la stessa etichetta.
    let cat = n.cats[0];
    if (n.suit && garments!.some((g) => g.category === "giacca completo")) cat = "pantalone completo";
    const id = cats.find((c) => c.name === cat)?.id;
    const q = new URLSearchParams({ dopo: "/benvenuto?passo=capi" });
    if (id) q.set("categoria", String(id));
    if (n.suit) q.set("completo", "completo 1");
    navigate(`/guardaroba/nuovo?${q}`);
  }

  return (
    <div>
      <Intro title="I primi capi">
        <p>Con questi pochi pezzi posso già proporti un completo e un informale. Fotografali su un fondo chiaro: lo sfondo lo tolgo io.</p>
        <p>Il resto lo aggiungi quando vuoi. Finché manca qualcosa, la schermata Domani ti dice cosa.</p>
      </Intro>
      <p className="mb-2 text-sm font-medium">{total} su {NEEDS.length}</p>
      <ul className="mb-4 divide-y divide-border rounded-lg border border-border">
        {NEEDS.map((n) => (
          <li key={n.label} className="flex items-center gap-3 p-3 text-sm">
            <span className={cn("flex h-5 w-5 shrink-0 items-center justify-center rounded-full border",
              done(n) ? "border-primary bg-primary text-primary-foreground" : "border-border")}>
              {done(n) && <Check className="h-3 w-3" />}
            </span>
            <span className="flex-1">
              <span className="block">{n.label}</span>
              <span className="text-xs text-muted-foreground">{n.suit ? n.hint : `${have(n)} di ${n.count}, ${n.hint}`}</span>
            </span>
            {!done(n) && (
              <Button size="sm" variant="outline" onClick={() => shoot(n)}><Camera className="h-4 w-4" /> Foto</Button>
            )}
          </li>
        ))}
      </ul>
      <Button className="w-full" onClick={onDone}>{total === NEEDS.length ? "Inizia" : "Inizia, il resto dopo"}</Button>
    </div>
  );
}
