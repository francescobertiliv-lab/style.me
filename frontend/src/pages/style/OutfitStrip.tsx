import type { Item } from "@/lib/api";
import { media } from "@/lib/utils";

export function OutfitStrip({ items }: { items: Item[] }) {
  return (
    <div className="flex gap-2 overflow-x-auto rounded-lg bg-muted/50 p-2">
      {items.map((i) => (
        <div key={i.id} className="w-14 shrink-0 text-center">
          {i.cutout ? <img src={media(i.cutout)} alt={i.name} className="h-14 w-14 object-contain" />
            : <div className="h-14 w-14 rounded border-2 border-dashed border-accent" style={{ background: i.color_hex }} />}
          <p className="truncate text-[10px]">{i.id === -1 ? "nuovo" : i.name}</p>
        </div>
      ))}
    </div>
  );
}
