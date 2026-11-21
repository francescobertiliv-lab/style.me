import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Check, ImagePlus, X } from "lucide-react";
import { api, type Category, type City } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { cutout, resize } from "@/lib/image";
import { cn, media } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, PageTitle, inputCls } from "@/components/Section";

type Job = { key: string; file: File; preview: string; state: "attesa" | "lavoro" | "fatto" | "errore";
  name?: string; cutout?: string | null; error?: string };

/** Importa in serie: scegli la categoria, selezioni tante foto dal Rullino, l'app le lavora una per una. */
export default function Import() {
  const { data: cats } = useApi<Category[]>("/categories");
  const { data: cities } = useApi<City[]>("/cities");
  const [cat, setCat] = useState<number | null>(null);
  const [city, setCity] = useState<number | "">("");
  const [cut, setCut] = useState(true);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [running, setRunning] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const patch = (key: string, p: Partial<Job>) => setJobs((js) => js.map((j) => (j.key === key ? { ...j, ...p } : j)));

  async function run(list: Job[]) {
    setRunning(true);
    // Una foto alla volta: il telefono resta reattivo e se qualcosa va storto si perde una foto, non tutte.
    for (const j of list) {
      patch(j.key, { state: "lavoro" });
      try {
        const photo = await resize(j.file);
        const c = cut ? await cutout(photo) : null;
        const form = new FormData();
        form.append("photo", photo, "foto.jpg");
        if (c) form.append("cutout", c, "ritaglio.png");
        form.append("category_id", String(cat));
        if (city) form.append("city_id", String(city));
        const r = await api.post<{ id: number; name: string; cutout: string | null }>("/garments/quick", form);
        patch(j.key, { state: "fatto", name: r.name, cutout: r.cutout });
      } catch (e) {
        patch(j.key, { state: "errore", error: (e as Error).message });
      }
    }
    setRunning(false);
  }

  function pick(files: FileList | null) {
    if (!files?.length || !cat) return;
    const added = Array.from(files).map((file, i) => ({
      key: `${Date.now()}-${i}`, file, preview: URL.createObjectURL(file), state: "attesa" as const,
    }));
    setJobs((js) => [...js, ...added]);
    if (!running) run(added);
  }

  const done = jobs.filter((j) => j.state === "fatto").length;
  const failed = jobs.filter((j) => j.state === "errore");
  const catName = cats?.find((c) => c.id === cat)?.name;

  return (
    <div className="space-y-4">
      <PageTitle title="Importa in serie" back />
      {!jobs.length && (
        <p className="text-sm text-muted-foreground">
          Scegli la categoria, poi seleziona dal Rullino tutte le foto di quel tipo. Nome e colore li propongo io;
          dopo li controlli in “Da sistemare”.
        </p>
      )}

      <Field label="Che cosa importi">
        <div className="flex flex-wrap gap-2">
          {cats?.map((c) => (
            <button key={c.id} disabled={running} onClick={() => setCat(c.id)}
              className={cn("rounded-full border px-3 py-1 text-sm capitalize",
                cat === c.id ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card")}>
              {c.name}
            </button>
          ))}
        </div>
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Dove sono">
          <select className={inputCls} value={city} disabled={running} onChange={(e) => setCity(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Città di casa</option>
            {cities?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Field>
        <label className="flex items-end gap-2 pb-3 text-sm">
          <input type="checkbox" checked={cut} disabled={running} onChange={(e) => setCut(e.target.checked)} />
          Togli lo sfondo
        </label>
      </div>

      <input ref={input} type="file" accept="image/*" multiple hidden onChange={(e) => { pick(e.target.files); e.target.value = ""; }} />
      <Button className="w-full" disabled={!cat || running} onClick={() => input.current?.click()}>
        <ImagePlus className="h-4 w-4" /> {cat ? `Scegli le foto: ${catName}` : "Prima scegli la categoria"}
      </Button>

      {jobs.length > 0 && (
        <Card><CardContent className="space-y-3 pt-4">
          <div className="space-y-1">
            <p className="text-sm font-medium">{done} di {jobs.length} pronte{failed.length ? `, ${failed.length} non riuscite` : ""}</p>
            <div className="h-1.5 rounded-full bg-muted">
              <div className="h-1.5 rounded-full bg-primary transition-all" style={{ width: `${(100 * (done + failed.length)) / jobs.length}%` }} />
            </div>
            {running && <p className="text-xs text-muted-foreground">Tieni l'app aperta e lo schermo acceso finché finisce. Puoi cambiare categoria quando la barra è piena.</p>}
          </div>
          <div className="grid grid-cols-4 gap-2">
            {jobs.map((j) => (
              <div key={j.key} className="relative aspect-square overflow-hidden rounded-md border border-border bg-muted">
                <img src={j.cutout ? media(j.cutout) : j.preview} alt="" className={cn("h-full w-full object-contain", j.state === "attesa" && "opacity-40")} />
                {j.state === "lavoro" && <span className="absolute inset-0 animate-pulse bg-primary/20" />}
                {j.state === "fatto" && <Check className="absolute right-1 top-1 h-4 w-4 rounded-full bg-primary p-0.5 text-primary-foreground" />}
                {j.state === "errore" && <X className="absolute right-1 top-1 h-4 w-4 rounded-full bg-destructive p-0.5 text-white" />}
              </div>
            ))}
          </div>
          {failed.length > 0 && !running && (
            <Button variant="outline" size="sm" onClick={() => run(failed)}>Riprova le {failed.length} non riuscite</Button>
          )}
          {!running && done > 0 && (
            <Link to="/guardaroba/da-sistemare"><Button className="w-full">Controlla i capi importati</Button></Link>
          )}
        </CardContent></Card>
      )}
    </div>
  );
}
