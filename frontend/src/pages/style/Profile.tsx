import { useEffect, useState } from "react";
import { api, type ColorFamily } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, inputCls } from "@/components/Section";

type Prof = { height_cm: number | null; build: string | null; coloring: string | null; sizes: Record<string, string>;
  fit_notes: string | null; budget_min: number | null; budget_max: number | null };
type Palette = { id: number; name: string; source: string; active: number; colors: { family: string; role: string; hex: string }[] };
type Rule = { id: number; kind: string; params: Record<string, unknown>; description: string; active: number };
const SIZE_KEYS = ["camicia", "giacca", "pantalone", "scarpe", "maglia"];
const ROLES = [["", "—"], ["base", "base"], ["da_aggiungere", "da aggiungere"], ["evita", "da evitare"]];

export default function Profile() {
  const { data: p } = useApi<Prof>("/profile");
  const { data: palettes, reload: reloadPal } = useApi<Palette[]>("/palettes");
  const { data: fams } = useApi<ColorFamily[]>("/color-families");
  const { data: rules, reload: reloadRules } = useApi<Rule[]>("/style-rules");
  const [f, setF] = useState<Prof | null>(null);
  const [saved, setSaved] = useState(false);
  useEffect(() => { if (p) setF(p); }, [p]);
  if (!f) return null;
  const active = palettes?.find((x) => x.active);
  const roleOf = (fam: string) => active?.colors.find((c) => c.family === fam)?.role ?? "";

  async function save() {
    await api.put("/profile", f);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function consultant() {
    const name = prompt("Nome della palette (es. 'Autunno profondo – consulente')");
    if (!name || !active) return;
    await api.post("/palettes", { name, source: "consulente", colors: active.colors.map(({ family, role }) => ({ family, role })) });
    reloadPal();
  }

  return (
    <div className="space-y-4">
      <Card><CardContent className="space-y-3 pt-4">
        <p className="font-medium">Fisico e vestibilità</p>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Altezza (cm)"><input className={inputCls} inputMode="numeric" value={f.height_cm ?? ""} onChange={(e) => setF({ ...f, height_cm: Number(e.target.value) || null })} /></Field>
          <Field label="Corporatura"><input className={inputCls} value={f.build ?? ""} onChange={(e) => setF({ ...f, build: e.target.value })} /></Field>
        </div>
        <Field label="Colori (capelli, occhi, carnagione)"><input className={inputCls} value={f.coloring ?? ""} onChange={(e) => setF({ ...f, coloring: e.target.value })} /></Field>
        <Field label="Note di vestibilità"><textarea className={inputCls + " h-24 py-2"} value={f.fit_notes ?? ""} onChange={(e) => setF({ ...f, fit_notes: e.target.value })} /></Field>
        <div className="grid grid-cols-3 gap-2">
          {SIZE_KEYS.map((k) => (
            <Field key={k} label={`Taglia ${k}`}><input className={inputCls} value={f.sizes[k] ?? ""} onChange={(e) => setF({ ...f, sizes: { ...f.sizes, [k]: e.target.value } })} /></Field>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Budget minimo €"><input className={inputCls} inputMode="numeric" value={f.budget_min ?? ""} onChange={(e) => setF({ ...f, budget_min: Number(e.target.value) || null })} /></Field>
          <Field label="Budget massimo €"><input className={inputCls} inputMode="numeric" value={f.budget_max ?? ""} onChange={(e) => setF({ ...f, budget_max: Number(e.target.value) || null })} /></Field>
        </div>
        <Button onClick={save}>{saved ? "Salvato" : "Salva"}</Button>
      </CardContent></Card>

      <Card><CardContent className="space-y-3 pt-4">
        <div className="flex items-center justify-between">
          <p className="font-medium">Palette: {active?.name}</p>
          <Button size="sm" variant="outline" onClick={consultant}>Palette della consulente</Button>
        </div>
        <p className="text-xs text-muted-foreground">Quando fai l'analisi, crea la palette della consulente e correggi i ruoli: sostituisce la stima.</p>
        <div className="grid grid-cols-2 gap-2">
          {fams?.map((fm) => (
            <label key={fm.name} className="flex items-center gap-2 text-sm">
              <span className="h-5 w-5 shrink-0 rounded-full border border-border" style={{ background: fm.hex }} />
              <span className="flex-1 truncate">{fm.name}</span>
              <select className="rounded border border-border bg-transparent text-xs" value={roleOf(fm.name)}
                onChange={async (e) => { await api.put(`/palettes/${active!.id}/colors`, { family: fm.name, role: e.target.value }); reloadPal(); }}>
                {ROLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
          ))}
        </div>
        {palettes && palettes.length > 1 && (
          <div className="text-xs text-muted-foreground">
            Altre palette: {palettes.filter((x) => !x.active).map((x) => (
              <button key={x.id} className="mr-2 underline" onClick={async () => { await api.post(`/palettes/${x.id}/activate`); reloadPal(); }}>{x.name}</button>
            ))}
          </div>
        )}
      </CardContent></Card>

      <Card><CardContent className="space-y-2 pt-4">
        <p className="font-medium">Regole di stile</p>
        {rules?.map((r) => (
          <label key={r.id} className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={!!r.active} onChange={async (e) => {
              await api.put(`/style-rules/${r.id}`, { ...r, active: e.target.checked ? 1 : 0 });
              reloadRules();
            }} />
            {r.description}
          </label>
        ))}
      </CardContent></Card>
    </div>
  );
}
