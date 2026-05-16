import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { listPatternUrls, PATTERN_MAX_SLOTS } from "@/lib/sindicompany/condominios-db";
import { PatternSlot } from "./pattern-slot";
import { DashboardShell } from "../shell";

export default async function PatternsPage() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  let urls: (string | null)[] = Array(PATTERN_MAX_SLOTS).fill(null);
  try {
    urls = await listPatternUrls();
  } catch {
    // Bucket inacessível — segue com slots vazios
  }

  return (
    <DashboardShell>
    <main className="max-w-5xl mx-auto px-6 py-12">
      <Link
        href="/sindicompany/dashboard"
        className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
      >
        ← Voltar
      </Link>

      <header className="mb-8">
        <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
          Tema · Padrões geométricos
        </div>
        <h1 className="text-3xl font-bold text-onix-900 mb-2">
          Patterns de fundo
        </h1>
        <p className="text-sm text-g60 max-w-2xl">
          Imagens que vão como detalhe sutil no fundo de todas as páginas
          (com baixa opacidade). Suba até 20 patterns — eles ciclam ao
          longo das páginas. Suportado: JPG, PNG, WebP. Máx 20MB cada.
          Recomenda-se imagens de pelo menos 1500px no maior lado.
        </p>
      </header>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {Array.from({ length: PATTERN_MAX_SLOTS }, (_, i) => i + 1).map((slot) => (
          <PatternSlot
            key={slot}
            slot={slot}
            initialUrl={urls[slot - 1]}
          />
        ))}
      </div>

      <div className="mt-8 text-xs text-g60">
        <strong className="text-onix-900">Como funciona:</strong> ao subir um
        pattern, ele substitui o slot existente. Se você deixar todos os 10
        slots preenchidos, cada página da revista mostra um pattern diferente
        no ciclo. Slots vazios são pulados.
      </div>
    </main>
    </DashboardShell>
  );
}
