import { useState } from "react";
import { useParams } from "react-router-dom";
import { AlertTriangle, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { PageTitle, inputCls } from "@/components/Section";
import type { PackLine } from "./TripDetail";

const SECTIONS: Record<string, string> = {
  documenti: "Documenti", elettronica: "Elettronica", kit: "Kit", vestiti: "Vestiti", altro: "Altro",
};

export function Checklist({ phase }: { phase: "andata" | "ritorno" }) {
  const { id } = useParams();
  const { data, reload, setData } = useApi<{ packing: PackLine[] }>(`/trips/${id}`);
  const [extra, setExtra] = useState("");
  if (!data) return null;
  const lines = data.packing.filter((p) => p.phase === phase);
  const must = lines.filter((p) => p.must_have);
  const rest = lines.filter((p) => !p.must_have);

  async function toggle(p: PackLine) {
    setData({ ...data!, packing: data!.packing.map((x) => (x.id === p.id ? { ...x, checked: x.checked ? 0 : 1 } : x)) });
    await api.patch(`/packing/${p.id}`, { checked: !p.checked });
  }

  async function add() {
    if (!extra.trim()) return;
    await api.post(`/trips/${id}/packing`, { phase, label: extra.trim() });
    setExtra("");
    reload();
  }

  const Row = (p: PackLine) => (
    <button key={p.id} onClick={() => toggle(p)}
      className={cn("flex w-full items-center gap-3 rounded-lg border p-3 text-left",
        p.must_have && !p.checked ? "border-accent bg-accent/5" : "border-border bg-card")}>
      <span className={cn("flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2",
        p.checked ? "border-primary bg-primary text-primary-foreground" : "border-border")}>{p.checked ? "✓" : ""}</span>
      <span className={cn("flex-1 text-sm", p.checked && "text-muted-foreground line-through")}>{p.label}</span>
      {p.qty > 1 && <span className="text-sm text-muted-foreground">×{p.qty}</span>}
    </button>
  );

  return (
    <div className="space-y-4">
      {must.length > 0 && (
        <section className="space-y-2">
          <h2 className="flex items-center gap-1 text-sm font-semibold text-accent"><AlertTriangle className="h-4 w-4" />Da non dimenticare</h2>
          {must.map(Row)}
        </section>
      )}
      {Object.entries(SECTIONS).map(([k, v]) => {
        const ls = rest.filter((p) => p.section === k);
        return ls.length ? (
          <section key={k} className="space-y-2">
            <h2 className="text-sm font-semibold text-muted-foreground">{v}</h2>
            {ls.map(Row)}
          </section>
        ) : null;
      })}
      <div className="flex gap-2">
        <input className={inputCls} value={extra} onChange={(e) => setExtra(e.target.value)} placeholder="Aggiungi una cosa" />
        <Button variant="outline" size="icon" aria-label="Aggiungi" onClick={add}><Plus className="h-4 w-4" /></Button>
      </div>
    </div>
  );
}

export default function Packing() {
  const { id } = useParams();
  const [msg, setMsg] = useState("");
  async function close() {
    try {
      const r = await api.post<{ moved: number }>(`/trips/${id}/packed`);
      setMsg(`Valigia chiusa: ${r.moved} capi segnati “in valigia”. Buon viaggio.`);
    } catch (e) {
      setMsg((e as Error).message);
    }
  }
  return (
    <div>
      <PageTitle title="Valigia" back />
      <Checklist phase="andata" />
      <Button className="mt-6 w-full" onClick={close}>Valigia fatta</Button>
      {msg && <p className="mt-3 text-center text-sm">{msg}</p>}
    </div>
  );
}
