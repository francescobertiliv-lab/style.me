import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api, SLOT_LABEL, type Item, type SwapOptions } from "@/lib/api";
import { media } from "@/lib/utils";
import { Button } from "@/components/ui/button";

function Thumb({ item }: { item: Item }) {
  const src = media(item.cutout ?? item.photo);
  return src ? (
    <img src={src} alt="" className="h-14 w-14 shrink-0 rounded-md bg-[#FAF9F6] object-contain" />
  ) : (
    <span className="h-14 w-14 shrink-0 rounded-md" style={{ background: item.color_hex }} />
  );
}

/** Foglio dal basso: cosa posso mettere al posto di un pezzo. */
export default function SwapSheet({ outfitId, slot, onClose, onDone }: {
  outfitId: number; slot: string; onClose: () => void; onDone: () => void;
}) {
  const [data, setData] = useState<SwapOptions | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<SwapOptions>(`/outfits/${outfitId}/options?slot=${slot}`).then(setData).catch((e) => setError(e.message));
  }, [outfitId, slot]);

  async function swap(add: Item[]) {
    if (!data) return;
    setBusy(true);
    try {
      await api.post(`/outfits/${outfitId}/swap`, {
        remove_ids: data.current.map((i) => i.id), add_ids: add.map((i) => i.id),
      });
      onDone();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const adding = data && data.current.length === 0;
  const title = data && data.current.length > 1 ? "Completo" : SLOT_LABEL[slot] ?? slot;

  return (
    <div className="fixed inset-0 z-50 flex items-end bg-black/40" onClick={onClose}>
      <div className="mx-auto max-h-[80vh] w-full max-w-xl overflow-y-auto rounded-t-2xl bg-card p-4 pb-[max(env(safe-area-inset-bottom),1rem)]"
        onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center">
          <p className="flex-1 font-medium">{adding ? `Aggiungi: ${title.toLowerCase()}` : `Cambia: ${title.toLowerCase()}`}</p>
          <button onClick={onClose} aria-label="Chiudi" className="rounded-lg p-1 hover:bg-muted"><X className="h-5 w-5" /></button>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!data && !error && <p className="py-6 text-center text-sm text-muted-foreground">Cerco cosa sta bene col resto…</p>}
        {data && data.options.length === 0 && (
          <p className="py-4 text-sm text-muted-foreground">
            Niente di pulito che stia bene col resto. Prova a cambiare prima un altro pezzo.
          </p>
        )}
        <ul className="space-y-2">
          {data?.options.map((opt) => (
            <li key={opt.map((i) => i.id).join("-")}>
              <button disabled={busy} onClick={() => swap(opt)}
                className="flex w-full items-center gap-3 rounded-lg border border-border p-2 text-left hover:bg-muted disabled:opacity-50">
                {opt.map((i) => <Thumb key={i.id} item={i} />)}
                <span className="text-sm">{opt.map((i) => i.name).join(" + ")}</span>
              </button>
            </li>
          ))}
        </ul>
        {data?.removable && (
          <Button variant="outline" className="mt-3 w-full" disabled={busy} onClick={() => swap([])}>
            Senza {title.toLowerCase()}
          </Button>
        )}
      </div>
    </div>
  );
}
