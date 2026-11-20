import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { Backpack, CalendarDays, Palette, Plane, Settings as SettingsIcon, Shirt } from "lucide-react";
import { cn } from "@/lib/utils";
import Tomorrow from "@/pages/Tomorrow";
import Login from "@/pages/Login";
import Settings from "@/pages/Settings";
import Wardrobe from "@/pages/wardrobe/Wardrobe";
import NewGarment from "@/pages/wardrobe/NewGarment";
import GarmentDetail from "@/pages/wardrobe/GarmentDetail";
import History from "@/pages/wardrobe/History";
import Tailor from "@/pages/wardrobe/Tailor";
import Trips from "@/pages/trips/Trips";
import TripForm from "@/pages/trips/TripForm";
import TripDetail from "@/pages/trips/TripDetail";
import Packing from "@/pages/trips/Packing";
import Return from "@/pages/trips/Return";
import Templates from "@/pages/trips/Templates";
import Kits from "@/pages/kits/Kits";
import Style from "@/pages/style/Style";

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
          <SettingsIcon className="h-5 w-5" />
        </NavLink>
      </header>
      <main className="flex-1 px-4 pb-28">
        <Routes>
          <Route path="/" element={<Tomorrow />} />
          <Route path="/guardaroba" element={<Wardrobe />} />
          <Route path="/guardaroba/nuovo" element={<NewGarment />} />
          <Route path="/guardaroba/:id" element={<GarmentDetail />} />
          <Route path="/storico" element={<History />} />
          <Route path="/sarta" element={<Tailor />} />
          <Route path="/viaggi" element={<Trips />} />
          <Route path="/viaggi/nuovo" element={<TripForm />} />
          <Route path="/viaggi/modelli" element={<Templates />} />
          <Route path="/viaggi/:id" element={<TripDetail />} />
          <Route path="/viaggi/:id/modifica" element={<TripForm />} />
          <Route path="/viaggi/:id/valigia" element={<Packing />} />
          <Route path="/viaggi/:id/rientro" element={<Return />} />
          <Route path="/kit" element={<Kits />} />
          <Route path="/kit/:tab" element={<Kits />} />
          <Route path="/stile" element={<Style />} />
          <Route path="/stile/:tab" element={<Style />} />
          <Route path="/impostazioni" element={<Settings />} />
          <Route path="*" element={<Tomorrow />} />
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
