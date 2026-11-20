import { useState } from "react";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageTitle, inputCls } from "@/components/Section";

type Line = { id: number; template_id: number | null; section: string; label: string; qty: number; kit_id: number | null;
  item_id: number | null; applies_if: string; must_have: number; on_return: number };
type Data = { templates: { id: number; name: string; from_calendar: number; spare_outfits: number; lines: Line[] }[]; common: Line[] };
const WHEN: Record<string, string> = { sempre: "sempre", fuori_schengen: "fuori Schengen", fuori_ue: "fuori UE" };
const SECTIONS = ["documenti", "elettronica", "kit", "vestiti", "altro"];

function Lines({ lines, templateId, reload }: { lines: Line[]; templateId: number | null; reload: () => void }) {
  const [label, setLabel] = useState("");
  const [section, setSection] = useState("altro");
  const [when, setWhen] = useState("sempre");

  async function update(l: Line, patch: Partial<Line>) {
    await api.put(`/trip-template-lines/${l.id}`, { ...l, ...patch });
    reload();
  }
  async function add() {
    if (!label.trim()) return;
    await api.post("/trip-template-lines", { template_id: templateId, section, label: label.trim(), applies_if: when });
    setLabel("");
    reload();
  }
  return (
    <div className="space-y-2">
      {lines.map((l) => (
        <div key={l.id} className="rounded-md border border-border p-2 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium">{l.label}</span>
            <button aria-label="Togli" onClick={async () => { await api.del(`/trip-template-lines/${l.id}`); reload(); }}>
              <Trash2 className="h-4 w-4 text-muted-foreground" />
            </button>
          </div>
          <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
            <select value={l.applies_if} onChange={(e) => update(l, { applies_if: e.target.value })} className="bg-transparent">
              {Object.entries(WHEN).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <label className="flex items-center gap-1"><input type="checkbox" checked={!!l.must_have} onChange={(e) => update(l, { must_have: e.target.checked ? 1 : 0 })} />in cima</label>
            <label className="flex items-center gap-1"><input type="checkbox" checked={!!l.on_return} onChange={(e) => update(l, { on_return: e.target.checked ? 1 : 0 })} />anche al ritorno</label>
          </div>
        </div>
      ))}
      <div className="grid grid-cols-[1fr_auto] gap-2">
        <input className={inputCls} value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Nuova voce" />
        <Button variant="outline" onClick={add}>Aggiungi</Button>
        <div className="col-span-2 flex gap-2">
          <select className={inputCls} value={section} onChange={(e) => setSection(e.target.value)}>{SECTIONS.map((s) => <option key={s}>{s}</option>)}</select>
          <select className={inputCls} value={when} onChange={(e) => setWhen(e.target.value)}>
            {Object.entries(WHEN).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </div>
    </div>
  );
}

export default function Templates() {
  const { data, reload } = useApi<Data>("/trip-templates");
  const [name, setName] = useState("");
  if (!data) return null;
  return (
    <div className="space-y-4">
      <PageTitle title="Modelli di viaggio" back />
      <Card><CardContent className="space-y-2 pt-4">
        <p className="font-medium">Per tutti i viaggi</p>
        <Lines lines={data.common} templateId={null} reload={reload} />
      </CardContent></Card>
      {data.templates.map((t) => (
        <Card key={t.id}><CardContent className="space-y-2 pt-4">
          <p className="font-medium">{t.name} {t.from_calendar ? <span className="text-xs text-muted-foreground">(dal calendario PE)</span> : null}</p>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">Outfit di scorta
            <input type="number" min={0} max={3} value={t.spare_outfits} className="w-14 rounded border border-border px-1"
              onChange={async (e) => { await api.put(`/trip-templates/${t.id}`, { ...t, spare_outfits: Number(e.target.value) }); reload(); }} />
          </label>
          <Lines lines={t.lines} templateId={t.id} reload={reload} />
        </CardContent></Card>
      ))}
      <div className="flex gap-2">
        <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="Nuovo tipo di viaggio" />
        <Button variant="outline" onClick={async () => { if (name) { await api.post("/trip-templates", { name }); setName(""); reload(); } }}>Crea</Button>
      </div>
    </div>
  );
}
