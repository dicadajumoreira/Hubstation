import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  LOGO_MAX_SLOTS,
  listLogoUrls,
} from "@/lib/sindicompany/condominios-db";
import { LogoSlot } from "./logo-slot";
import { DashboardShell } from "../shell";

export default async function LogosPage() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  let urls: (string | null)[] = Array(LOGO_MAX_SLOTS).fill(null);
  try {
    urls = await listLogoUrls();
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
            Tema · Identidade visual
          </div>
          <h1 className="text-3xl font-bold text-onix-900 mb-2">Logotipos</h1>
          <p className="text-sm text-g60 max-w-2xl">
            Variantes do logotipo da marca (principal, monocromático, branco
            sobre fundo escuro, versão reduzida, etc.). Suba até 10 versões.
            Suporta JPG, PNG, WebP e SVG. Máx 10MB cada. Recomendado SVG ou
            PNG transparente.
          </p>
        </header>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: LOGO_MAX_SLOTS }, (_, i) => i + 1).map(
            (slot) => (
              <LogoSlot key={slot} slot={slot} initialUrl={urls[slot - 1]} />
            ),
          )}
        </div>

        <div className="mt-8 text-xs text-g60">
          <strong className="text-onix-900">Convenção sugerida:</strong>{" "}
          slot 1 = principal · slot 2 = branco/escuro · slot 3 = monocromático
          · slot 4 = símbolo isolado. Slots vazios são pulados.
        </div>
      </main>
    </DashboardShell>
  );
}
