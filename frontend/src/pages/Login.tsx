import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function Login() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/auth/login", { password });
      const me = await api.get<{ onboarded: boolean }>("/auth/me");
      // Ricarico la pagina: così l'app rilegge subito che sei entrato.
      window.location.assign(me.onboarded ? "/" : "/benvenuto");
    } catch {
      setError("Password sbagliata.");
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto flex min-h-full max-w-xs flex-col justify-center gap-4 px-4">
      <h1 className="text-2xl font-semibold tracking-tight">Style.me</h1>
      <input
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        className="h-11 rounded-lg border border-border bg-card px-3"
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit">Entra</Button>
    </form>
  );
}
