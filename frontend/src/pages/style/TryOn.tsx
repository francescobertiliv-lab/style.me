import { useRef, useState } from "react";
import { Camera } from "lucide-react";
import { api, type Category, type ColorFamily, type Item } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { cutout, resize } from "@/lib/image";
import { Button } from "@/components/ui/button";
import { Field, inputCls } from "@/components/Section";
import { OutfitStrip } from "./OutfitStrip";

type Result = { piece: Item; outfits: Item[][]; verdict: string; wishlist_id: number | null };

export default function TryOn() {
  const { data: cats } = useApi<Category[]>("/categories");
  const { data: fams } = useApi<ColorFamily[]>("/color-families");
  const [category, setCategory] = useState("overshirt");
  const [family, setFamily] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [res, setRes] = useState<Result | null>(null);
  const [msg, setMsg] = useState("");
  const input = useRef<HTMLInputElement>(null);

  async function run(save = false) {
    setMsg("Provo gli abbinamenti…");
    const form = new FormData();
    form.append("category", category);
    if (family) form.append("color_family", family);
    if (url) form.append("url", url);
    form.append("save", save ? "1" : "0");
    if (file) {
      const photo = await resize(file);
      form.append("photo", photo, "foto.jpg");
      const cut = await cutout(photo, setMsg);
      if (cut) form.append("cutout", cut, "ritaglio.png");
    }
    try {
      setRes(await api.post<Result>("/try-on", form));
      setMsg(save ? "Salvato nei desideri." : "");
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">Salva l'immagine del capo dal negozio online (o fai uno screenshot) e caricala qui. Se non hai l'immagine, scegli solo il colore.</p>
      <input ref={input} type="file" accept="image/*" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <Button variant="outline" className="w-full" onClick={() => input.current?.click()}>
        <Camera className="h-4 w-4" />{file ? file.name : "Carica l'immagine del capo"}
      </Button>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Che capo è">
          <select className={inputCls} value={category} onChange={(e) => setCategory(e.target.value)}>
            {cats?.filter((c) => !["giacca completo", "pantalone completo"].includes(c.name)).map((c) => <option key={c.id}>{c.name}</option>)}
          </select>
        </Field>
        <Field label="Colore">
          <select className={inputCls} value={family} onChange={(e) => setFamily(e.target.value)}>
            <option value="">{file ? "dalla foto" : "scegli…"}</option>
            {fams?.map((f) => <option key={f.name}>{f.name}</option>)}
          </select>
        </Field>
      </div>
      <Field label="Link del negozio (facoltativo)"><input className={inputCls} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" /></Field>
      <Button className="w-full" onClick={() => run(false)}>Vedi gli abbinamenti</Button>
      {msg && <p className="text-center text-sm text-muted-foreground">{msg}</p>}
      {res && (
        <div className="space-y-2">
          <p className="font-medium">{res.verdict}</p>
          {res.outfits.map((o, i) => <OutfitStrip key={i} items={o} />)}
          {!res.wishlist_id && <Button variant="outline" className="w-full" onClick={() => run(true)}>Metti nei desideri</Button>}
        </div>
      )}
    </div>
  );
}
