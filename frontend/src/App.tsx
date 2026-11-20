import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { Backpack, CalendarDays, Palette, Plane, Settings, Shirt } from "lucide-react";
import { cn } from "@/lib/utils";
import Tomorrow from "@/pages/Tomorrow";
import Login from "@/pages/Login";
import Soon from "@/pages/Soon";

const tabs = [
  { to: "/", label: "Domani", icon: CalendarDays },
  { to: "/guardaroba", label: "Guardaroba", icon: Shirt },
  { to: "/viaggi", label: "Viaggi", icon: Plane },
  { to: "/kit", label: "Kit", icon: Backpack },
  { to: "/stile", label: "Stile", icon: Palette },
];

export default function App() {
  const { pathname } = useLocation();
  if (pathname === "/login") return <Login />;
  return (
    <div className="mx-auto flex min-h-full max-w-xl flex-col">
      <header className="flex items-center justify-between px-4 pt-[max(env(safe-area-inset-top),1rem)] pb-2">
        <span className="text-lg font-semibold tracking-tight">Style.me</span>
        <NavLink to="/impostazioni" aria-label="Impostazioni" className="rounded-lg p-2 hover:bg-muted">
          <Settings className="h-5 w-5" />
        </NavLink>
      </header>
      <main className="flex-1 px-4 pb-28">
        <Routes>
          <Route path="/" element={<Tomorrow />} />
          <Route path="*" element={<Soon />} />
        </Routes>
      </main>
      <nav className="fixed inset-x-0 bottom-0 border-t border-border bg-card/95 backdrop-blur pb-[env(safe-area-inset-bottom)]">
        <ul className="mx-auto grid max-w-xl grid-cols-5">
          {tabs.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  cn("flex flex-col items-center gap-1 py-2.5 text-[11px]",
                    isActive ? "text-primary font-semibold" : "text-muted-foreground")}
              >
                <Icon className="h-5 w-5" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
