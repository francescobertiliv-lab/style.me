import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/hooks";
import { Card, CardContent } from "@/components/ui/card";
import { Empty } from "@/components/Section";

type Data = {
  chart: { family: string; hex: string; count: number; role: string }[];
  missing: { family: string; hex: string; role: string; missing_in: string[] }[];
  total: number; dark_share: number;
};
const ROLE: Record<string, string> = { base: "base", da_aggiungere: "da aggiungere", evita: "da evitare", fuori: "fuori palette" };

export default function Analysis() {
  const { data } = useApi<Data>("/analysis");
  if (!data) return null;
  if (!data.chart.length) return <Empty>Aggiungi qualche capo informale e qui vedi i tuoi colori.</Empty>;
  return (
    <div className="space-y-4">
      <Card><CardContent className="pt-4">
        <p className="mb-1 text-sm font-medium">I colori dei tuoi capi informali</p>
        <p className="mb-3 text-xs text-muted-foreground">{Math.round(data.dark_share * 100)}% sono scuri, su {data.total} capi.</p>
        <div style={{ height: Math.max(160, data.chart.length * 28) }}>
          <ResponsiveContainer>
            <BarChart data={data.chart} layout="vertical" margin={{ left: 8, right: 16 }}>
              <XAxis type="number" allowDecimals={false} hide />
              <YAxis type="category" dataKey="family" width={110} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v, _n, p) => [`${v} capi`, ROLE[(p.payload as { role: string }).role]]} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {data.chart.map((c) => <Cell key={c.family} fill={c.hex} stroke="#00000022" />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent></Card>
      {data.missing.length > 0 && (
        <Card><CardContent className="space-y-2 pt-4">
          <p className="text-sm font-medium">Colori della palette che non hai</p>
          {data.missing.map((m) => (
            <div key={m.family} className="flex items-center gap-3 text-sm">
              <span className="h-6 w-6 rounded-full border border-border" style={{ background: m.hex }} />
              <span className="flex-1">
                {m.family} <span className="text-xs text-muted-foreground">· {ROLE[m.role]}</span>
              </span>
            </div>
          ))}
        </CardContent></Card>
      )}
    </div>
  );
}
