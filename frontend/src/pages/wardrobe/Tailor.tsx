import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { media } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Empty, PageTitle } from "@/components/Section";

type Job = { id: number; garment_id: number; garment: string; cutout: string | null; kind: string; note: string | null; status: string };
const GROUPS = [
  { key: "da_portare", title: "Da portare", next: "dalla_sarta", action: "L'ho portato" },
  { key: "dalla_sarta", title: "Dalla sarta", next: "fatto", action: "Ritirato" },
  { key: "fatto", title: "Fatti", next: null, action: "" },
];

export default function Tailor() {
  const { data, reload } = useApi<Job[]>("/tailor");
  async function move(id: number, status: string) {
    await api.patch(`/tailor/${id}`, { status });
    reload();
  }
  return (
    <div>
      <PageTitle title="Sarta" back />
      {data && !data.length && <Empty>Nessun lavoro. Aggiungili dalla scheda di un capo.</Empty>}
      {GROUPS.map((g) => {
        const jobs = (data ?? []).filter((j) => j.status === g.key);
        if (!jobs.length) return null;
        return (
          <section key={g.key} className="mb-5">
            <h2 className="mb-2 text-sm font-semibold text-muted-foreground">{g.title}</h2>
            <div className="space-y-2">
              {jobs.map((j) => (
                <div key={j.id} className="flex items-center gap-3 rounded-lg border border-border bg-card p-3">
                  {j.cutout && <img src={media(j.cutout)} alt="" className="h-12 w-12 object-contain" />}
                  <Link to={`/guardaroba/${j.garment_id}`} className="min-w-0 flex-1 text-sm">
                    <p className="truncate font-medium">{j.garment}</p>
                    <p className="text-muted-foreground">{j.kind.replace("_", " ")}{j.note ? `: ${j.note}` : ""}</p>
                  </Link>
                  {g.next && <Button size="sm" variant="outline" onClick={() => move(j.id, g.next!)}>{g.action}</Button>}
                </div>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
