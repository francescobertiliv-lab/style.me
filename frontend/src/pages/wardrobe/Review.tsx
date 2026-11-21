import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Category, type ColorFamily, type Garment } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { media } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Empty, Field, PageTitle, inputCls } from "@/components/Section";

const PATTERNS = ["tinta unita", "righe", "quadri", "gessato", "regimental", "pois", "fantasia"];
const FORMALITY = ["", "sportivo", "casual", "smart casual", "elegante", "completo scuro"];

/** Da sistemare: i capi importati in serie, uno alla volta. Correggi solo quello che è sbagliato. */
export default function Review() {
  const { data: list, reload } = useApi<Garment[]>("/garments?to_review=1");
  const { data: cats } = useApi<Category[]>("/categories");
  const { data: fams } = useApi<ColorFamily[]>("/color-families");
  const [d, setD] = useState<Garment | null>(null);
  const [busy, setBusy] = useState(false);
  const g = list?.[0];

  useEffect(() => { setD(g ? { ...g } : null); }, [g]);

  if (!list) return null;
  if (!g || !d) {
    return (
      <div>
        <PageTitle title="Da sistemare" back />
        <Empty>Tutto controllato. <Link to="/guardaroba/importa" className="underline">Importa altre foto</Link></Empty>
      </div>
    );
  }

  const changed = (["name", "category_id", "color_family", "pattern", "formality"] as const).some((k) => d[k] !== g[k]);

  async function next(action: "ok" | "scarta") {
    setBusy(true);
    try {
      if (action === "scarta") await api.del(`/garments/${g!.id}`);
      else if (!changed) await api.post(`/garments/${g!.id}/reviewed`);
      else {
        const full = await api.get<Garment & { colors: unknown[] }>(`/garments/${g!.id}`);
        const fam = fams?.find((f) => f.name === d!.color_family);
        await api.put(`/garments/${g!.id}`, {
          ...full, name: d!.name, category_id: d!.category_id, color_family: d!.color_family,
          color_hex: fam && d!.color_family !== g!.color_family ? fam.hex : full.color_hex,
          pattern: d!.pattern, formality: d!.formality,
        });
      }
      await reload();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <PageTitle title="Da sistemare" back action={<span className="text-sm text-muted-foreground">{list.length} da vedere</span>} />
      <Card className="overflow-hidden">
        <img src={media(g.cutout ?? g.photo)} alt={g.name} className="aspect-square w-full bg-[#FAF9F6] object-contain p-4" />
        <CardContent className="space-y-3 pt-3">
          <Field label="Nome"><input className={inputCls} value={d.name} onChange={(e) => setD({ ...d, name: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Categoria">
              <select className={inputCls} value={d.category_id} onChange={(e) => setD({ ...d, category_id: Number(e.target.value) })}>
                {cats?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </Field>
            <Field label="Colore">
              <select className={inputCls} value={d.color_family} onChange={(e) => setD({ ...d, color_family: e.target.value })}>
                {fams?.map((f) => <option key={f.name} value={f.name}>{f.name}</option>)}
              </select>
            </Field>
            <Field label="Fantasia">
              <select className={inputCls} value={d.pattern} onChange={(e) => setD({ ...d, pattern: e.target.value })}>
                {PATTERNS.map((p) => <option key={p}>{p}</option>)}
              </select>
            </Field>
            <Field label="Quanto è elegante">
              <select className={inputCls} value={d.formality} onChange={(e) => setD({ ...d, formality: Number(e.target.value) })}>
                {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}, {FORMALITY[n]}</option>)}
              </select>
            </Field>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" disabled={busy} onClick={() => next("scarta")}>Scarta</Button>
            <Link to={`/guardaroba/${g.id}`} className="flex-1"><Button variant="ghost" className="w-full">Scheda completa</Button></Link>
            <Button className="flex-1" disabled={busy} onClick={() => next("ok")}>{changed ? "Salva" : "Va bene"}</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
