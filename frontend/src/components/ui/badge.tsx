import * as React from "react";
import { cn } from "@/lib/utils";

type Props = React.HTMLAttributes<HTMLSpanElement> & { tone?: "neutral" | "primary" | "accent" | "warning" };

export function Badge({ className, tone = "neutral", ...props }: Props) {
  const tones = {
    neutral: "bg-muted text-muted-foreground",
    primary: "bg-primary text-primary-foreground",
    accent: "bg-accent/10 text-accent",
    warning: "bg-amber-100 text-amber-800",
  };
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", tones[tone], className)}
      {...props}
    />
  );
}
