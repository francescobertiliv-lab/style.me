import { useNavigate, useParams } from "react-router-dom";
import { PageTitle, Tabs } from "@/components/Section";
import Analysis from "./Analysis";
import Suggestions from "./Suggestions";
import TryOn from "./TryOn";
import Wishlist from "./Wishlist";
import Profile from "./Profile";

type Tab = "analisi" | "suggerimenti" | "prova" | "desideri" | "profilo";

export default function Style() {
  const { tab = "analisi" } = useParams();
  const navigate = useNavigate();
  return (
    <div>
      <PageTitle title="Stile" />
      <Tabs<Tab> value={tab as Tab} onChange={(t) => navigate(`/stile/${t}`)} options={[
        { value: "analisi", label: "Colori" }, { value: "suggerimenti", label: "Da comprare" },
        { value: "prova", label: "Prova" }, { value: "desideri", label: "Desideri" }, { value: "profilo", label: "Profilo" },
      ]} />
      {tab === "analisi" && <Analysis />}
      {tab === "suggerimenti" && <Suggestions />}
      {tab === "prova" && <TryOn />}
      {tab === "desideri" && <Wishlist />}
      {tab === "profilo" && <Profile />}
    </div>
  );
}
