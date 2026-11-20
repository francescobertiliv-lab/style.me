import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { media } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Empty } from "@/components/Section";

type Wish = { id: number; description: string; category: string | null; color_family: string | null; url: string | null;
  cutout: string | null; price_eur: number | null; status: string };

export default function Wishlist() {
  const { data, reload } = useApi<Wish[]>("/wishlist");
  if (data && !data.length) return <Empty>La lista è vuota. Aggiungi dai suggerimenti o dalla prova.</Empty>;
  return (
    <div className="space-y-2">
      {data?.map((w) => (
        <div key={w.id} className="flex items-center gap-3 rounded-lg border border-border bg-card p-3 text-sm">
          {w.cutout && <img src={media(w.cutout)} alt="" className="h-12 w-12 object-contain" />}
          <div className="min-w-0 flex-1">
            <p className="font-medium">{w.description}</p>
            {w.url && <a href={w.url} target="_blank" rel="noreferrer" className="truncate text-xs text-muted-foreground underline">negozio</a>}
          </div>
          <Link to={`/guardaroba/nuovo?desiderio=${w.id}`}><Button size="sm">Comprato</Button></Link>
          <Button size="sm" variant="ghost" onClick={async () => { await api.del(`/wishlist/${w.id}`); reload(); }}>Togli</Button>
        </div>
      ))}
    </div>
  );
}
