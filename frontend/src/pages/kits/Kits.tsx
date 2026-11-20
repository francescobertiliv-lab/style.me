import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Minus, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Empty, PageTitle, Tabs, inputCls } from "@/components/Section";

type InvItem = { id: number; name: string; owned_qty: number; consumable: number; running_low: number;
  refill_from: string | null; per_night: number; notes: string | null; kits: string[]; qty?: number };
type Kit = { id: number; name: string; place: string | null; notes: string | null; items: InvItem[] };
type Shop = { id: number; name: string; qty: number | null; reason: string };
type Tab = "kit" | "inventario" | "spesa";

function KitsTab() {
  const { data: kits, reload } = useApi<Kit[]>("/kits");
  const { data: items } = useApi<InvItem[]>("/items");
  const [adding, setAdding] = useState<Record<number, string>>({});
  const [name, setName] = useState("");

  async function setQty(kit: number, item: number, qty: number) {
    if (qty <= 0) await api.del(`/kits/${kit}/items/${item}`);
    else await api.put(`/kits/${kit}/items`, { item_id: item, qty });
    reload();
  }

  return (
    <div className="space-y-3">
      {kits?.map((k) => (
        <Card key={k.id}><CardContent className="space-y-2 pt-4">
          <div className="flex items-center justify-between">
            <p className="font-medium">{k.name}</p>
            <input className="w-28 rounded border border-border bg-transparent px-2 py-1 text-right text-xs text-muted-foreground"
              defaultValue={k.place ?? ""} placeholder="dove sta"
              onBlur={(e) => api.put(`/kits/${k.id}`, { name: k.name, place: e.target.value || null, notes: k.notes })} />
          </div>
          {k.items.map((i) => (
            <div key={i.id} className="flex items-center justify-between text-sm">
              <span className={cn(i.owned_qty < (i.qty ?? 1) && "text-accent")}>{i.name}</span>
              <span className="flex items-center gap-1">
                <button aria-label="Meno" onClick={() => setQty(k.id, i.id, (i.qty ?? 1) - 1)}><Minus className="h-4 w-4" /></button>
                <span className="w-5 text-center">{i.qty}</span>
                <button aria-label="Più" onClick={() => setQty(k.id, i.id, (i.qty ?? 1) + 1)}><Plus className="h-4 w-4" /></button>
              </span>
            </div>
          ))}
          <div className="flex gap-2">
            <select className={inputCls} value={adding[k.id] ?? ""} onChange={(e) => setAdding({ ...adding, [k.id]: e.target.value })}>
              <option value="">Aggiungi un oggetto…</option>
              {items?.filter((i) => !k.items.some((x) => x.id === i.id)).map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
            </select>
            <Button variant="outline" onClick={() => adding[k.id] && setQty(k.id, Number(adding[k.id]), 1)}>Ok</Button>
          </div>
          <button className="text-xs text-muted-foreground" onClick={async () => {
            if (confirm(`Elimino il kit ${k.name}?`)) { await api.del(`/kits/${k.id}`); reload(); }
          }}>Elimina kit</button>
        </CardContent></Card>
      ))}
      <div className="flex gap-2">
        <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="Nuovo kit" />
        <Button variant="outline" onClick={async () => { if (name) { await api.post("/kits", { name }); setName(""); reload(); } }}>Crea</Button>
      </div>
    </div>
  );
}

function InventoryTab() {
  const { data, reload } = useApi<InvItem[]>("/items");
  const [name, setName] = useState("");
  async function save(i: InvItem, patch: Partial<InvItem>) {
    const b = { ...i, ...patch };
    await api.put(`/items/${i.id}`, { name: b.name, owned_qty: b.owned_qty, consumable: b.consumable, running_low: b.running_low,
      refill_from: b.refill_from || null, per_night: b.per_night, notes: b.notes });
    reload();
  }
  return (
    <div className="space-y-2">
      {data?.map((i) => (
        <div key={i.id} className="rounded-lg border border-border bg-card p-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium">{i.name}</span>
            <span className="flex items-center gap-2">
              <button aria-label="Meno" onClick={() => save(i, { owned_qty: Math.max(0, i.owned_qty - 1) })}><Minus className="h-4 w-4" /></button>
              <span className="w-6 text-center">{i.owned_qty}</span>
              <button aria-label="Più" onClick={() => save(i, { owned_qty: i.owned_qty + 1 })}><Plus className="h-4 w-4" /></button>
            </span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {i.kits.map((k) => <Badge key={k}>{k}</Badge>)}
            <Button size="sm" variant={i.running_low ? "accent" : "outline"} className="h-7"
              onClick={() => save(i, { running_low: i.running_low ? 0 : 1 })}>{i.running_low ? "Quasi finito" : "Segna quasi finito"}</Button>
            <input className="w-36 rounded border border-border bg-transparent px-2 py-1" placeholder="chi chiedere"
              defaultValue={i.refill_from ?? ""} onBlur={(e) => e.target.value !== (i.refill_from ?? "") && save(i, { refill_from: e.target.value })} />
            <button aria-label="Elimina" onClick={async () => { if (confirm(`Elimino ${i.name}?`)) { await api.del(`/items/${i.id}`); reload(); } }}>
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      ))}
      <div className="flex gap-2">
        <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="Nuovo oggetto" />
        <Button variant="outline" onClick={async () => { if (name) { await api.post("/items", { name, owned_qty: 1 }); setName(""); reload(); } }}>Aggiungi</Button>
      </div>
    </div>
  );
}

function ShoppingTab() {
  const { data } = useApi<Shop[]>("/shopping-list");
  const { data: rem, reload } = useApi<{ id: number; title: string; due_at: string }[]>("/reminders");
  return (
    <div className="space-y-4">
      {data && !data.length && <Empty>Non ti manca niente.</Empty>}
      <div className="space-y-2">
        {data?.map((s) => (
          <div key={`${s.id}${s.reason}`} className="flex justify-between rounded-lg border border-border bg-card p-3 text-sm">
            <span>{s.qty ? `${s.qty} × ` : ""}{s.name}</span>
            <span className="text-muted-foreground">{s.reason}</span>
          </div>
        ))}
      </div>
      {!!rem?.length && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground">Promemoria</h2>
          {rem.map((r) => (
            <div key={r.id} className="flex items-center justify-between rounded-lg border border-border bg-card p-3 text-sm">
              <span>{r.title}</span>
              <Button size="sm" variant="outline" onClick={async () => { await api.post(`/reminders/${r.id}/done`); reload(); }}>Fatto</Button>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}

export default function Kits() {
  const { tab = "kit" } = useParams();
  const navigate = useNavigate();
  return (
    <div>
      <PageTitle title="Kit e inventario" />
      <Tabs<Tab> value={tab as Tab} onChange={(t) => navigate(t === "kit" ? "/kit" : `/kit/${t}`)}
        options={[{ value: "kit", label: "Kit" }, { value: "inventario", label: "Inventario" }, { value: "spesa", label: "Lista spesa" }]} />
      {tab === "kit" && <KitsTab />}
      {tab === "inventario" && <InventoryTab />}
      {tab === "spesa" && <ShoppingTab />}
    </div>
  );
}
