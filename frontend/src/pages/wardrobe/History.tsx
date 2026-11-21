import { useApi } from "@/lib/hooks";
import { formatDay, media } from "@/lib/utils";
import { Empty, PageTitle } from "@/components/Section";

type Worn = { id: number; date: string; dress_code: string; rating: number | null; image: string | null;
  items: { id: number; name: string; color_hex: string }[] };

export default function History() {
  const { data } = useApi<Worn[]>("/history");
  return (
    <div>
      <PageTitle title="Cosa ho indossato" back />
      {data && !data.length && <Empty>Ancora niente. Segna “L'ho messo” dalla schermata Domani.</Empty>}
      <div className="space-y-3">
        {data?.map((o) => (
          <div key={o.id} className="flex gap-3 rounded-lg border border-border bg-card p-3">
            {o.image ? <img src={media(o.image)} alt="" className="h-24 w-20 rounded-md object-cover" /> :
              <div className="flex h-24 w-20 flex-wrap gap-1">{o.items.map((i) => <span key={i.id} className="h-5 w-5 rounded" style={{ background: i.color_hex }} />)}</div>}
            <div className="min-w-0 text-sm">
              <p className="font-medium capitalize">{formatDay(o.date)} {o.rating === 1 ? "👍" : o.rating === -1 ? "👎" : ""}</p>
              <p className="text-muted-foreground">{o.dress_code}</p>
              <p className="truncate text-muted-foreground">{o.items.map((i) => i.name).join(", ")}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
