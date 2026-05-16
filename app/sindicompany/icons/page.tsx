import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  ICON_MAX_SLOTS,
  listIconUrls,
} from "@/lib/sindicompany/condominios-db";
import { IconSlot } from "./icon-slot";
import { DashboardShell } from "../shell";

export default async function IconsPage() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  let urls: (string | null)[] = Array(ICON_MAX_SLOTS).fill(null);
  try {
    urls = await listIconUrls();
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
            Tema · Iconografia
          </div>
          <h1 className="text-3xl font-bold text-onix-900 mb-2">Icons</h1>
          <p className="text-sm text-g60 max-w-2xl">
            Biblioteca de ícones da marca pra usar em revistas e carrosséis.
            Suba até 20 ícones — eles ficam disponíveis pra a engine puxar
            pelo número do slot. Suporta JPG, PNG, WebP e SVG. Máx 10MB cada.
          </p>
        </header>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {Array.from({ length: ICON_MAX_SLOTS }, (_, i) => i + 1).map(
            (slot) => (
              <IconSlot key={slot} slot={slot} initialUrl={urls[slot - 1]} />
            ),
          )}
        </div>

        <div className="mt-8 text-xs text-g60">
          <strong className="text-onix-900">Como funciona:</strong> SVG é
          recomendado pra ícones (escala sem perda). Slots vazios são pulados.
          Pra substituir, suba um arquivo novo no mesmo slot.
        </div>
      </main>
    </DashboardShell>
  );
}
