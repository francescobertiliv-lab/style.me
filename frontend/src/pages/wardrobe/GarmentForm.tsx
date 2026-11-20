import { useState } from "react";
import type { Category, City, ColorFamily } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Field, inputCls } from "@/components/Section";
import { Button } from "@/components/ui/button";

export type GarmentDraft = {
  name: string; category_id: number | ""; color_hex: string; color_family: string; colors: { hex: string; share: number }[];
  pattern: string; formality: number; weight: number; material: string; rain_ok: number; rain_gear: number;
  set_key: string; size: string; brand: string; price_eur: string; status: string; city_id: number | "";
  photo: string; cutout: string | null; notes: string;
};

const PATTERNS = ["tinta unita", "righe", "quadri", "gessato", "regimental", "pois", "fantasia"];
const FORMALITY = ["", "Sportivo", "Casual", "Smart casual", "Elegante", "Completo scuro"];
const WEIGHT = ["", "Leggero", "Medio", "Pesante"];

export function GarmentForm({ initial, onSubmit, submitLabel }: {
  initial: GarmentDraft; onSubmit: (d: GarmentDraft) => Promise<void>; submitLabel: string;
}) {
  const [d, setD] = useState(initial);
  const [busy, setBusy] = useState(false);
  const { data: cats } = useApi<Category[]>("/categories");
  const { data: cities } = useApi<City[]>("/cities");
  const { data: fams } = useApi<ColorFamily[]>("/color-families");
  const set = <K extends keyof GarmentDraft>(k: K, v: GarmentDraft[K]) => setD((x) => ({ ...x, [k]: v }));

  function pickCategory(id: number) {
    const c = cats?.find((x) => x.id === id);
    setD((x) => ({ ...x, category_id: id, ...(c ? { formality: c.default_formality, weight: c.default_weight } : {}) }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try { await onSubmit(d); } finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <Field label="Nome"><input className={inputCls} required value={d.name} onChange={(e) => set("name", e.target.value)} placeholder="Chino cammello" /></Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Categoria">
          <select className={inputCls} required value={d.category_id} onChange={(e) => pickCategory(Number(e.target.value))}>
            <option value="">Scegli…</option>
            {cats?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Field>
        <Field label="Fantasia">
          <select className={inputCls} value={d.pattern} onChange={(e) => set("pattern", e.target.value)}>
            {PATTERNS.map((p) => <option key={p}>{p}</option>)}
          </select>
        </Field>
      </div>
      <Field label="Colore">
        <div className="flex items-center gap-2">
          <input type="color" value={d.color_hex} onChange={(e) => set("color_hex", e.target.value.toUpperCase())}
            className="h-11 w-14 rounded-lg border border-border bg-card" />
          <select className={inputCls} value={d.color_family} onChange={(e) => set("color_family", e.target.value)}>
            {fams?.map((f) => <option key={f.name}>{f.name}</option>)}
          </select>
        </div>
        {d.colors.length > 1 && (
          <div className="mt-1 flex gap-1">
            {d.colors.map((c) => <button type="button" key={c.hex} onClick={() => set("color_hex", c.hex)}
              title={c.hex} className="h-6 w-6 rounded-full border border-border" style={{ background: c.hex }} />)}
          </div>
        )}
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label={`Formalità: ${FORMALITY[d.formality]}`}>
          <input type="range" min={1} max={5} value={d.formality} onChange={(e) => set("formality", Number(e.target.value))} className="w-full" />
        </Field>
        <Field label={`Peso: ${WEIGHT[d.weight]}`}>
          <input type="range" min={1} max={3} value={d.weight} onChange={(e) => set("weight", Number(e.target.value))} className="w-full" />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Materiale"><input className={inputCls} value={d.material} onChange={(e) => set("material", e.target.value)} placeholder="lana, cotone, scamosciato…" /></Field>
        <Field label="Città">
          <select className={inputCls} required value={d.city_id} onChange={(e) => set("city_id", Number(e.target.value))}>
            {cities?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Field>
      </div>
      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2"><input type="checkbox" checked={!d.rain_ok} onChange={(e) => set("rain_ok", e.target.checked ? 0 : 1)} />Da evitare con la pioggia</label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={!!d.rain_gear} onChange={(e) => set("rain_gear", e.target.checked ? 1 : 0)} />Va bene con la pioggia (cappotto, impermeabile)</label>
      </div>
      <details className="rounded-lg border border-border bg-card p-3 text-sm">
        <summary className="cursor-pointer font-medium">Altri dettagli</summary>
        <div className="mt-3 space-y-3">
          <Field label="Completo (stesso nome per giacca e pantalone)"><input className={inputCls} value={d.set_key} onChange={(e) => set("set_key", e.target.value)} placeholder="completo blu" /></Field>
          <div className="grid grid-cols-3 gap-2">
            <Field label="Taglia"><input className={inputCls} value={d.size} onChange={(e) => set("size", e.target.value)} /></Field>
            <Field label="Marca"><input className={inputCls} value={d.brand} onChange={(e) => set("brand", e.target.value)} /></Field>
            <Field label="Prezzo €"><input className={inputCls} inputMode="decimal" value={d.price_eur} onChange={(e) => set("price_eur", e.target.value)} /></Field>
          </div>
          <Field label="Note"><textarea className={inputCls + " h-20 py-2"} value={d.notes} onChange={(e) => set("notes", e.target.value)} /></Field>
        </div>
      </details>
      <Button type="submit" className="w-full" disabled={busy}>{busy ? "Salvo…" : submitLabel}</Button>
    </form>
  );
}

export function toPayload(d: GarmentDraft) {
  return {
    ...d, category_id: Number(d.category_id), city_id: Number(d.city_id), set_key: d.set_key || null,
    price_eur: d.price_eur ? Number(d.price_eur.replace(",", ".")) : null, material: d.material || null,
    size: d.size || null, brand: d.brand || null, notes: d.notes || null,
  };
}
