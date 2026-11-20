import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Pencil, Scissors, Trash2 } from "lucide-react";
import { api, STATUS_LABEL, type City, type Garment } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { formatDay, media } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, PageTitle, inputCls } from "@/components/Section";
import { GarmentForm, toPayload, type GarmentDraft } from "./GarmentForm";

type Detail = Garment & {
  worn: { date: string; rating: number | null }[];
  tailor: { id: number; kind: string; note: string | null; status: string }[];
};

const KINDS: Record<string, string> = {
  orlo: "Orlo", spalle: "Spalle", lunghezza_giacca: "Lunghezza giacca", stringere: "Stringere", altro: "Altro",
};

export default function GarmentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: g, reload } = useApi<Detail>(`/garments/${id}`);
  const { data: cities } = useApi<City[]>("/cities");
  const [edit, setEdit] = useState(false);
  const [kind, setKind] = useState("orlo");
  const [note, setNote] = useState("");

  if (!g) return null;

  async function quick(body: { status?: string; city_id?: number }) {
    await api.patch(`/garments/${id}`, body);
    reload();
  }

  async function addTailor() {
    await api.post("/tailor", { garment_id: Number(id), kind, note: note || null });
    setNote("");
    reload();
  }

  async function archive() {
    if (!confirm("Tolgo questo capo dal guardaroba? Resta nello storico.")) return;
    await api.del(`/garments/${id}`);
    navigate("/guardaroba");
  }

  if (edit) {
    const draft: GarmentDraft = {
      name: g.name, category_id: g.category_id, color_hex: g.color_hex, color_family: g.color_family, colors: g.colors ?? [],
      pattern: g.pattern, formality: g.formality, weight: g.weight, material: g.material ?? "", rain_ok: g.rain_ok,
      rain_gear: g.rain_gear, set_key: g.set_key ?? "", size: g.size ?? "", brand: g.brand ?? "",
      price_eur: g.price_eur?.toString() ?? "", status: g.status, city_id: g.city_id, photo: g.photo, cutout: g.cutout, notes: g.notes ?? "",
    };
    return (
      <div>
        <PageTitle title="Modifica" back />
        <GarmentForm initial={draft} submitLabel="Salva" onSubmit={async (d) => {
          await api.put(`/garments/${id}`, toPayload(d));
          setEdit(false);
          reload();
        }} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageTitle title={g.name} back action={
        <Button variant="ghost" size="icon" aria-label="Modifica" onClick={() => setEdit(true)}><Pencil className="h-4 w-4" /></Button>
      } />
      <div className="rounded-lg border border-border bg-card p-4">
        {/* Fase 2: qui comparirà il modello 3D, se disponibile. Senza 3D resta la foto. */}
        <img src={media(g.cutout || g.photo)} alt={g.name} className="mx-auto h-72 object-contain" />
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge>{g.category}</Badge>
        <Badge><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full" style={{ background: g.color_hex }} />{g.color_family}</Badge>
        <Badge>{g.pattern}</Badge>
        {g.material && <Badge>{g.material}</Badge>}
        {g.set_key && <Badge tone="accent">{g.set_key}</Badge>}
      </div>

      <Card>
        <CardContent className="space-y-3 pt-4">
          <p className="text-sm font-medium">Stato</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(STATUS_LABEL).map(([k, v]) => (
              <Button key={k} size="sm" variant={g.status === k ? "default" : "outline"} onClick={() => quick({ status: k })}>{v}</Button>
            ))}
          </div>
          <Field label="Dove si trova">
            <select className={inputCls} value={g.city_id} onChange={(e) => quick({ city_id: Number(e.target.value) })}>
              {cities?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3 pt-4">
          <p className="flex items-center gap-2 text-sm font-medium"><Scissors className="h-4 w-4" />Sarta</p>
          {g.tailor.map((t) => (
            <p key={t.id} className="text-sm">{KINDS[t.kind]}{t.note ? `: ${t.note}` : ""} <span className="text-muted-foreground">({t.status.replace("_", " ")})</span></p>
          ))}
          <div className="flex gap-2">
            <select className={inputCls + " w-40"} value={kind} onChange={(e) => setKind(e.target.value)}>
              {Object.entries(KINDS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input className={inputCls} placeholder="Nota" value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <Button variant="outline" size="sm" onClick={addTailor}>Aggiungi alla lista della sarta</Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-1 pt-4 text-sm">
          <p className="font-medium">Quando l'ho messo</p>
          {g.worn.length ? g.worn.map((w) => (
            <p key={w.date} className="capitalize text-muted-foreground">{formatDay(w.date)} {w.rating === 1 ? "👍" : w.rating === -1 ? "👎" : ""}</p>
          )) : <p className="text-muted-foreground">Mai, finora.</p>}
        </CardContent>
      </Card>

      <Button variant="ghost" className="w-full text-destructive" onClick={archive}><Trash2 className="h-4 w-4" />Togli dal guardaroba</Button>
    </div>
  );
}
