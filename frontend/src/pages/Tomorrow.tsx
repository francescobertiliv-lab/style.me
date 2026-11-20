import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CloudSun, MapPin, Plane, RefreshCw, ThumbsDown, ThumbsUp } from "lucide-react";
import { Link } from "react-router-dom";
import { api, type DayPlan } from "@/lib/api";
import { cn, formatDay, media } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const CODES = [
  { value: "completo", label: "Completo" },
  { value: "informale", label: "Informale" },
  { value: "libero", label: "Non vado in ufficio" },
] as const;

export default function Tomorrow() {
  const [plan, setPlan] = useState<DayPlan | null>(null);
  const [pick, setPick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (refresh = false) => {
    setBusy(true);
    setError("");
    try {
      setPlan(await api.get<DayPlan>(`/day/tomorrow${refresh ? "?refresh=1" : ""}`));
      setPick(0);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function override(code: string | null) {
    if (!plan) return;
    await api.put(`/day/${plan.date}/override`, { dress_code: code });
    load(true);
  }

  async function worn(outfitId: number) {
    await api.post(`/outfits/${outfitId}/worn`);
    load();
  }

  async function rate(outfitId: number, rating: 1 | -1) {
    await api.post(`/outfits/${outfitId}/rate`, { rating });
    load();
  }

  if (error) return <p className="py-10 text-center text-destructive">{error}</p>;
  if (!plan) return <p className="py-10 text-center text-muted-foreground">Preparo domani…</p>;

  const outfit = plan.outfits[pick];

  return (
    <div className="space-y-4">
      <section className="space-y-2">
        <p className="text-sm capitalize text-muted-foreground">{formatDay(plan.date)}</p>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="primary" className="capitalize">{plan.dress_code}</Badge>
          <Badge>{plan.reason}</Badge>
          {plan.trip && (
            <Link to={`/viaggi/${plan.trip.id}`}>
              <Badge tone="accent"><Plane className="mr-1 h-3 w-3" />{plan.trip.destination}</Badge>
            </Link>
          )}
        </div>
        <p className="flex items-center gap-4 text-sm">
          <span className="flex items-center gap-1"><MapPin className="h-4 w-4" />{plan.city}</span>
          <span className="flex items-center gap-1"><CloudSun className="h-4 w-4" />{plan.weather_text}</span>
        </p>
      </section>

      {(!plan.weather_ok || !plan.calendar_ok) && (
        <Card className="border-amber-300 bg-amber-50">
          <CardContent className="flex gap-2 pt-4 text-sm text-amber-900">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {!plan.calendar_ok && "the361 non ha risposto: uso l'ultimo calendario salvato. "}
            {!plan.weather_ok && "Il meteo non ha risposto: niente filtri su pioggia e temperatura."}
          </CardContent>
        </Card>
      )}

      {plan.missing.length > 0 && (
        <Card>
          <CardContent className="space-y-1 pt-4 text-sm">
            <p className="font-medium">Cosa manca</p>
            {plan.missing.map((m) => <p key={m} className="text-muted-foreground">{m}</p>)}
          </CardContent>
        </Card>
      )}

      {outfit && (
        <Card className="overflow-hidden">
          {outfit.image ? (
            <img src={media(outfit.image)} alt="Outfit di domani" className="aspect-[9/11] w-full object-contain bg-[#FAF9F6]" />
          ) : (
            <div className="grid grid-cols-3 gap-2 p-3">
              {outfit.items.map((i) => (
                <div key={i.id} className="aspect-square rounded-md" style={{ background: i.color_hex }} />
              ))}
            </div>
          )}
          <CardContent className="space-y-3 pt-3">
            <ul className="space-y-1 text-sm">
              {outfit.items.map((i) => (
                <li key={i.id} className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full border border-border" style={{ background: i.color_hex }} />
                  <Link to={`/guardaroba/${i.id}`} className="hover:underline">{i.name}</Link>
                </li>
              ))}
            </ul>
            <div className="flex items-center gap-2">
              <Button variant={outfit.rating === 1 ? "default" : "outline"} size="icon" aria-label="Mi piace"
                onClick={() => rate(outfit.id, 1)}><ThumbsUp className="h-4 w-4" /></Button>
              <Button variant={outfit.rating === -1 ? "default" : "outline"} size="icon" aria-label="Non mi piace"
                onClick={() => rate(outfit.id, -1)}><ThumbsDown className="h-4 w-4" /></Button>
              <Button variant={outfit.status === "indossato" ? "default" : "outline"} size="sm"
                onClick={() => worn(outfit.id)}>{outfit.status === "indossato" ? "Indossato" : "L'ho messo"}</Button>
              <Button variant="ghost" className="ml-auto" disabled={busy} onClick={() => load(true)}>
                <RefreshCw className={cn("h-4 w-4", busy && "animate-spin")} /> Ricalcola
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {plan.outfits.length > 1 && (
        <div className="flex gap-2">
          {plan.outfits.map((o, idx) => (
            <Button key={o.id} variant={idx === pick ? "default" : "outline"} size="sm" onClick={() => setPick(idx)}>
              {idx === 0 ? "Proposta" : `Alternativa ${idx}`}
            </Button>
          ))}
        </div>
      )}

      <section className="space-y-2">
        <p className="text-sm font-medium">Domani è diverso?</p>
        <div className="flex flex-wrap gap-2">
          {CODES.map((c) => (
            <Button key={c.value} size="sm" variant={plan.overridden && plan.dress_code === c.value ? "default" : "outline"}
              onClick={() => override(c.value)}>{c.label}</Button>
          ))}
          {plan.overridden && <Button size="sm" variant="ghost" onClick={() => override(null)}>Torna al calendario</Button>}
        </div>
      </section>
    </div>
  );
}
