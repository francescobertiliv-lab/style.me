import { Link } from "react-router-dom";
import { Plus, Settings2 } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Empty, PageTitle } from "@/components/Section";

export type Trip = { id: number; destination: string; start_date: string; end_date: string; status: string;
  source: string; template: string; template_id: number; country: string; lat: number; lon: number;
  city_id: number | null; notes: string | null };

const fmt = (d: string) => new Date(d + "T12:00:00").toLocaleDateString("it-IT", { day: "numeric", month: "short" });

export default function Trips() {
  const { data } = useApi<Trip[]>("/trips");
  const today = new Date().toISOString().slice(0, 10);
  const next = (data ?? []).filter((t) => t.end_date >= today).reverse();
  const past = (data ?? []).filter((t) => t.end_date < today);
  const Row = (t: Trip) => (
    <Link key={t.id} to={`/viaggi/${t.id}`} className="flex items-center justify-between rounded-lg border border-border bg-card p-3">
      <div>
        <p className="font-medium">{t.destination}</p>
        <p className="text-sm text-muted-foreground">{fmt(t.start_date)} – {fmt(t.end_date)} · {t.template}</p>
      </div>
      {t.source === "the361" && <Badge>calendario PE</Badge>}
      {t.status === "in_corso" && <Badge tone="accent">in corso</Badge>}
    </Link>
  );
  return (
    <div>
      <PageTitle title="Viaggi" action={
        <div className="flex gap-1">
          <Link to="/viaggi/modelli"><Button variant="ghost" size="icon" aria-label="Modelli"><Settings2 className="h-5 w-5" /></Button></Link>
          <Link to="/viaggi/nuovo"><Button size="sm"><Plus className="h-4 w-4" />Viaggio</Button></Link>
        </div>
      } />
      {data && !data.length && <Empty>Nessun viaggio. Le plenarie arrivano da sole dal calendario.</Empty>}
      <div className="space-y-2">{next.map(Row)}</div>
      {past.length > 0 && <h2 className="mb-2 mt-6 text-sm font-semibold text-muted-foreground">Passati</h2>}
      <div className="space-y-2">{past.slice(0, 10).map(Row)}</div>
    </div>
  );
}
