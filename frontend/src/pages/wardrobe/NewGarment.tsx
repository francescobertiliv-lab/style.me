import { useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Camera } from "lucide-react";
import { api } from "@/lib/api";
import { cutout, resize } from "@/lib/image";
import { media } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { PageTitle } from "@/components/Section";
import { GarmentForm, toPayload, type GarmentDraft } from "./GarmentForm";

type Upload = {
  photo: string; cutout: string;
  proposal: { color_hex: string; color_family: string; colors: { hex: string; share: number }[]; pattern: string;
    category_id: number | null; formality: number; weight: number };
};

export default function NewGarment() {
  const [step, setStep] = useState<"foto" | "lavoro" | "dati">("foto");
  const [msg, setMsg] = useState("");
  const [draft, setDraft] = useState<GarmentDraft | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const wishlistId = params.get("desiderio");

  async function onFile(file: File) {
    try {
      await prepare(file);
    } catch (e) {
      setStep("foto");
      setMsg((e as Error).message);
    }
  }

  async function prepare(file: File) {
    setStep("lavoro");
    setMsg("Preparo la foto…");
    const photo = await resize(file);
    const cut = await cutout(photo, setMsg);
    setMsg("Leggo i colori…");
    const form = new FormData();
    form.append("photo", photo, "foto.jpg");
    if (cut) form.append("cutout", cut, "ritaglio.png");
    const up = await api.post<Upload>("/garments/photo", form);
    const cities = await api.get<{ id: number; is_home: number }[]>("/cities");
    const p = up.proposal;
    setDraft({
      name: "", category_id: p.category_id ?? "", color_hex: p.color_hex, color_family: p.color_family, colors: p.colors,
      pattern: p.pattern, formality: p.formality, weight: p.weight, material: "", rain_ok: 1, rain_gear: 0,
      set_key: "", size: "", brand: "", price_eur: "", status: "pulito",
      city_id: cities.find((c) => c.is_home)?.id ?? cities[0].id, photo: up.photo, cutout: up.cutout, notes: "",
    });
    setStep("dati");
  }

  async function save(d: GarmentDraft) {
    const r = await api.post<{ id: number }>(`/garments${wishlistId ? `?wishlist_id=${wishlistId}` : ""}`, toPayload(d));
    navigate(`/guardaroba/${r.id}`, { replace: true });
  }

  return (
    <div>
      <PageTitle title="Nuovo capo" back />
      {step === "foto" && (
        <div className="space-y-4 text-center">
          <p className="text-sm text-muted-foreground">Fotografa il capo steso su uno sfondo bianco, con buona luce e senza ombre forti.</p>
          <input ref={input} type="file" accept="image/*" capture="environment" className="hidden"
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
          <Button className="w-full" onClick={() => input.current?.click()}><Camera className="h-4 w-4" />Scatta o scegli la foto</Button>
          {msg && <p className="text-sm text-destructive">Non sono riuscito a caricare la foto: {msg}</p>}
          <p className="text-xs text-muted-foreground">La prima volta lo scontorno scarica il modello sul telefono: ci vuole qualche secondo in più.</p>
        </div>
      )}
      {step === "lavoro" && <p className="py-10 text-center text-muted-foreground">{msg}</p>}
      {step === "dati" && draft && (
        <div className="space-y-4">
          <img src={media(draft.cutout)} alt="Ritaglio" className="mx-auto h-56 object-contain" />
          <p className="text-sm text-muted-foreground">Ti propongo questi dati. Correggi quello che non va.</p>
          <GarmentForm initial={draft} onSubmit={save} submitLabel="Aggiungi al guardaroba" />
        </div>
      )}
    </div>
  );
}
