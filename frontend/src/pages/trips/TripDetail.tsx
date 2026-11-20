import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Briefcase, Home, Pencil, RefreshCw } from "lucide-react";
import { api, type Item } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { formatDay, media } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageTitle } from "@/components/Section";
import type { Trip } from "./Trips";

export type PackLine = { id: number; phase: string; section: string; label: string; qty: number; garment_id: number | null;
  must_have: number; checked: number; garment_status: string | null };
type Detail = Trip & {
  days: { date: string; dress_code: string; week_label: string; weather_text: string;
    outfit: { id: number; image: string | null; items: Item[]; missing: string | null } | null }[];
  packing: PackLine[];
};

export default function TripDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: t, reload } = useApi<Detail>(`/trips/${id}`);
  const [busy, setBusy] = useState(false);
  if (!t) return null;

  const notReady = t.packing.filter((p) => p.garment_id && p.garment_status && !["pulito", "valigia"].includes(p.garment_status));
  const andata = t.packing.filter((p) => p.phase === "andata");

  async function replan() {
    setBusy(true);
    await api.post(`/trips/${id}/plan`);
    await reload();
    setBusy(false);
  }

  async function cancel() {
    if (!confirm("Annullo questo viaggio?")) return;
    await api.del(`/trips/${id}`);
    navigate("/viaggi");
  }

  return (
    <div className="space-y-4">
      <PageTitle title={t.destination} back action={
        <Link to={`/viaggi/${id}/modifica`}><Button variant="ghost" size="icon" aria-label="Modifica"><Pencil className="h-4 w-4" /></Button></Link>
      } />
      <div className="grid grid-cols-2 gap-2">
        <Link to={`/viaggi/${id}/valigia`}><Button className="w-full"><Briefcase className="h-4 w-4" />Valigia ({andata.filter((p) => p.checked).length}/{andata.length})</Button></Link>
        <Link to={`/viaggi/${id}/rientro`}><Button variant="outline" className="w-full"><Home className="h-4 w-4" />Rientro</Button></Link>
      </div>
      {notReady.length > 0 && (
        <Card className="border-amber-300 bg-amber-50">
          <CardContent className="pt-4 text-sm text-amber-900">
            <p className="font-medium">Da preparare prima di partire</p>
            {notReady.map((p) => <p key={p.id}>{p.label}: {p.garment_status?.replace("_", " ")}</p>)}
          </CardContent>
        </Card>
      )}
      {t.days.map((d) => (
        <Card key={d.date}>
          <CardContent className="space-y-2 pt-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium capitalize">{formatDay(d.date)}</p>
              <Badge tone="primary">{d.dress_code}</Badge>
            </div>
            <p className="text-xs text-muted-foreground">{d.week_label} · {d.weather_text}</p>
            {d.outfit?.items.length ? (
              <div className="flex gap-2 overflow-x-auto">
                {d.outfit.items.map((i) => (
                  <Link to={`/guardaroba/${i.id}`} key={i.id} className="w-16 shrink-0 text-center">
                    {i.cutout ? <img src={media(i.cutout)} alt={i.name} className="h-16 w-16 object-contain" />
                      : <div className="h-16 w-16 rounded" style={{ background: i.color_hex }} />}
                    <p className="truncate text-[10px]">{i.name}</p>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-sm text-accent">
                {(d.outfit?.missing ? (JSON.parse(d.outfit.missing) as string[]) : []).join(" ") || "Nessun outfit valido: mancano capi puliti adatti."}
              </p>
            )}
          </CardContent>
        </Card>
      ))}
      <Button variant="outline" className="w-full" disabled={busy} onClick={replan}><RefreshCw className="h-4 w-4" />Ricalcola outfit e valigia</Button>
      <Button variant="ghost" className="w-full text-destructive" onClick={cancel}>Annulla il viaggio</Button>
    </div>
  );
}
