import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { History, Images, Plus, Scissors } from "lucide-react";
import { STATUS_LABEL, type City, type Garment } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { media } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Empty, PageTitle, inputCls } from "@/components/Section";

const SLOTS: Record<string, string> = {
  "": "Tutto", capospalla: "Capispalla", giacca: "Giacche", strato: "Maglioni", top: "Camicie e maglie",
  sotto: "Pantaloni", scarpe: "Scarpe", cravatta: "Cravatte", accessorio: "Accessori",
};

export default function Wardrobe() {
  const [slot, setSlot] = useState("");
  const [status, setStatus] = useState("");
  const [city, setCity] = useState("");
  const { data } = useApi<Garment[]>("/garments");
  const { data: cities } = useApi<City[]>("/cities");
  const todo = (data ?? []).filter((g) => g.to_review).length;

  const list = useMemo(() => (data ?? []).filter((g) =>
    (!slot || g.slot === slot) && (!status || g.status === status) && (!city || String(g.city_id) === city)), [data, slot, status, city]);

  return (
    <div>
      <PageTitle title="Guardaroba" action={
        <div className="flex gap-1">
          <Link to="/storico"><Button variant="ghost" size="icon" aria-label="Storico"><History className="h-5 w-5" /></Button></Link>
          <Link to="/sarta"><Button variant="ghost" size="icon" aria-label="Sarta"><Scissors className="h-5 w-5" /></Button></Link>
          <Link to="/guardaroba/importa"><Button variant="outline" size="sm"><Images className="h-4 w-4" />In serie</Button></Link>
          <Link to="/guardaroba/nuovo"><Button size="sm"><Plus className="h-4 w-4" />Capo</Button></Link>
        </div>
      } />
      {todo > 0 && (
        <Link to="/guardaroba/da-sistemare" className="mb-3 block rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {todo === 1 ? "1 capo importato da controllare" : `${todo} capi importati da controllare`} →
        </Link>
      )}
      <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
        {Object.entries(SLOTS).map(([k, v]) => (
          <button key={k} onClick={() => setSlot(k)}
            className={"whitespace-nowrap rounded-full border px-3 py-1 text-sm " +
              (slot === k ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card")}>{v}</button>
        ))}
      </div>
      <div className="mb-4 grid grid-cols-2 gap-2">
        <select className={inputCls} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Ogni stato</option>
          {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className={inputCls} value={city} onChange={(e) => setCity(e.target.value)}>
          <option value="">Ogni città</option>
          {cities?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>
      {data && !list.length && <Empty>Nessun capo qui. Aggiungi il primo con “Capo”.</Empty>}
      <div className="grid grid-cols-3 gap-3">
        {list.map((g) => (
          <Link key={g.id} to={`/guardaroba/${g.id}`} className="group">
            <div className="relative aspect-square overflow-hidden rounded-lg border border-border bg-muted">
              {g.cutout
                ? <img src={media(g.cutout)} alt={g.name} loading="lazy" className="h-full w-full object-contain p-2" />
                : <div className="h-full w-full" style={{ background: g.color_hex }} />}
              {g.status !== "pulito" && (
                <span className="absolute left-1 top-1 rounded bg-foreground/80 px-1.5 py-0.5 text-[10px] text-background">
                  {STATUS_LABEL[g.status]}
                </span>
              )}
            </div>
            <p className="mt-1 truncate text-xs">{g.name}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
