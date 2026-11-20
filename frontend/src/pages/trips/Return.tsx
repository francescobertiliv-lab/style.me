import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { PageTitle } from "@/components/Section";
import { Checklist } from "./Packing";
import type { PackLine } from "./TripDetail";

export default function Return() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data } = useApi<{ packing: PackLine[] }>(`/trips/${id}`);
  const [choices, setChoices] = useState<Record<number, string>>({});
  const clothes = (data?.packing ?? []).filter((p) => p.phase === "andata" && p.garment_id);

  async function done() {
    const all = Object.fromEntries(clothes.map((c) => [c.garment_id!, choices[c.garment_id!] ?? "da_lavare"]));
    await api.post(`/trips/${id}/return`, { choices: all });
    navigate("/guardaroba");
  }

  return (
    <div className="space-y-6">
      <PageTitle title="Rientro" back />
      <Checklist phase="ritorno" />
      {clothes.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground">A casa: cosa va lavato?</h2>
          {clothes.map((c) => {
            const v = choices[c.garment_id!] ?? "da_lavare";
            return (
              <div key={c.id} className="flex items-center justify-between rounded-lg border border-border bg-card p-3 text-sm">
                <span>{c.label}</span>
                <div className="flex gap-1">
                  {[["pulito", "Pulito"], ["da_lavare", "Da lavare"]].map(([k, l]) => (
                    <Button key={k} size="sm" variant={v === k ? "default" : "outline"}
                      onClick={() => setChoices({ ...choices, [c.garment_id!]: k })}>{l}</Button>
                  ))}
                </div>
              </div>
            );
          })}
        </section>
      )}
      <Button className="w-full" onClick={done}>Sono a casa</Button>
    </div>
  );
}
