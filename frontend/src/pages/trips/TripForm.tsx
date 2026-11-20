import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type City } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Field, PageTitle, inputCls } from "@/components/Section";
import type { Trip } from "./Trips";

type Place = { name: string; country: string; admin: string; lat: number; lon: number };
type Templates = { templates: { id: number; name: string }[] };

export default function TripForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: tpl } = useApi<Templates>("/trip-templates");
  const { data: cities } = useApi<City[]>("/cities");
  const { data: existing } = useApi<Trip>(id ? `/trips/${id}` : null);
  const [q, setQ] = useState("");
  const [places, setPlaces] = useState<Place[]>([]);
  const [f, setF] = useState({ template_id: 0, destination: "", lat: 0, lon: 0, country: "", start_date: "", end_date: "",
    city_id: "" as number | "", notes: "" });
  const [error, setError] = useState("");

  useEffect(() => {
    if (existing) setF({ ...existing, city_id: existing.city_id ?? "", notes: existing.notes ?? "" });
  }, [existing]);
  useEffect(() => {
    if (!f.template_id && tpl?.templates.length) setF((x) => ({ ...x, template_id: tpl.templates[0].id }));
  }, [tpl, f.template_id]);

  async function search() {
    setPlaces(await api.get<Place[]>(`/geocode?q=${encodeURIComponent(q)}`));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!f.country) return setError("Scegli la destinazione dall'elenco.");
    const body = { ...f, city_id: f.city_id || null, notes: f.notes || null };
    try {
      const r = id ? (await api.put(`/trips/${id}`, body), { id: Number(id) }) : await api.post<{ id: number }>("/trips", body);
      navigate(`/viaggi/${r.id}`, { replace: true });
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <PageTitle title={id ? "Modifica viaggio" : "Nuovo viaggio"} back />
      <form onSubmit={save} className="space-y-3">
        <Field label="Tipo">
          <select className={inputCls} value={f.template_id} onChange={(e) => setF({ ...f, template_id: Number(e.target.value) })}>
            {tpl?.templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </Field>
        <Field label="Destinazione">
          <div className="flex gap-2">
            <input className={inputCls} value={q || f.destination} onChange={(e) => setQ(e.target.value)} placeholder="Città" />
            <Button type="button" variant="outline" onClick={search}>Cerca</Button>
          </div>
        </Field>
        {places.length > 0 && (
          <div className="space-y-1">
            {places.map((p) => (
              <button type="button" key={`${p.lat}${p.lon}`} className="block w-full rounded-lg border border-border bg-card p-2 text-left text-sm"
                onClick={() => { setF({ ...f, destination: p.name, lat: p.lat, lon: p.lon, country: p.country }); setQ(""); setPlaces([]); }}>
                {p.name}, {p.admin} ({p.country})
              </button>
            ))}
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <Field label="Partenza"><input type="date" required className={inputCls} value={f.start_date} onChange={(e) => setF({ ...f, start_date: e.target.value })} /></Field>
          <Field label="Ritorno"><input type="date" required className={inputCls} value={f.end_date} onChange={(e) => setF({ ...f, end_date: e.target.value })} /></Field>
        </div>
        <Field label="Lì ho già dei vestiti?">
          <select className={inputCls} value={f.city_id} onChange={(e) => setF({ ...f, city_id: e.target.value ? Number(e.target.value) : "" })}>
            <option value="">No</option>
            {cities?.filter((c) => !c.is_home).map((c) => <option key={c.id} value={c.id}>Sì, quelli di {c.name}</option>)}
          </select>
        </Field>
        <Field label="Note"><input className={inputCls} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full">Prepara il viaggio</Button>
      </form>
    </div>
  );
}
