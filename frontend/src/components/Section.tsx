import { ChevronLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

export function PageTitle({ title, back, action }: { title: string; back?: boolean; action?: React.ReactNode }) {
  const navigate = useNavigate();
  return (
    <div className="mb-4 flex items-center gap-2">
      {back && (
        <button onClick={() => navigate(-1)} aria-label="Indietro" className="-ml-2 rounded-lg p-2 hover:bg-muted">
          <ChevronLeft className="h-5 w-5" />
        </button>
      )}
      <h1 className="flex-1 text-xl font-semibold tracking-tight">{title}</h1>
      {action}
    </div>
  );
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}

export const inputCls = "h-11 w-full rounded-lg border border-border bg-card px-3 text-sm";

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="py-8 text-center text-sm text-muted-foreground">{children}</p>;
}

export function Tabs<T extends string>({ value, onChange, options }: {
  value: T; onChange: (v: T) => void; options: { value: T; label: string }[];
}) {
  return (
    <div className="mb-4 flex gap-1 overflow-x-auto rounded-lg bg-muted p-1">
      {options.map((o) => (
        <button key={o.value} onClick={() => onChange(o.value)}
          className={"flex-1 whitespace-nowrap rounded-md px-3 py-1.5 text-sm " +
            (o.value === value ? "bg-card font-medium shadow-sm" : "text-muted-foreground")}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
