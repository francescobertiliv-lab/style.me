import { useApi } from "@/lib/hooks";
import type { Item } from "@/lib/api";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Empty } from "@/components/Section";
import { OutfitStrip } from "./OutfitStrip";

type S = { category: string; family: string; hex: string; description: string; why: string; budget: string; outfits: Item[][] };

export default function Suggestions() {
  const { data, loading } = useApi<{ sizes: Record<string, string>; items: S[] }>("/suggestions");
  if (loading && !data) return <Empty>Cerco i capi che fanno più outfit con quello che hai…</Empty>;
  if (!data?.items.length) return <Empty>Per ora nessun capo nuovo fa almeno 3 outfit con i tuoi. Aggiungi più capi al guardaroba.</Empty>;
  const sizes = Object.entries(data.sizes).map(([k, v]) => `${k} ${v}`).join(" · ");
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">Descrivo il capo, non un prodotto: i negozi li scegli tu.{sizes && ` Taglie: ${sizes}.`}</p>
      {data.items.map((s) => (
        <Card key={`${s.category}${s.family}`}><CardContent className="space-y-2 pt-4">
          <div className="flex items-center gap-3">
            <span className="h-8 w-8 rounded-full border border-border" style={{ background: s.hex }} />
            <div className="flex-1">
              <p className="font-medium">{s.description}</p>
              <p className="text-xs text-muted-foreground">{s.why} · budget {s.budget}</p>
            </div>
          </div>
          {s.outfits.map((o, i) => <OutfitStrip key={i} items={o} />)}
          <Button size="sm" variant="outline" onClick={() => api.post("/wishlist", { description: s.description, color_family: s.family, status: "desiderato" })}>
            Metti nei desideri
          </Button>
        </CardContent></Card>
      ))}
    </div>
  );
}
