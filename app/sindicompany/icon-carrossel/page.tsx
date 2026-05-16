import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  ICON_CARROSSEL_MAX_SLOTS,
  listIconCarrosselUrls,
} from "@/lib/sindicompany/condominios-db";
import { IconCarrosselSlot } from "./icon-carrossel-slot";
import { DashboardShell } from "../shell";

export default async function IconCarrosselPage() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  let urls: (string | null)[] = Array(ICON_CARROSSEL_MAX_SLOTS).fill(null);
  try {
    urls = await listIconCarrosselUrls();
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
            Tema · Carrossel Instagram
          </div>
          <h1 className="text-3xl font-bold text-onix-900 mb-2">
            Fundo Carrossel
          </h1>
          <p className="text-sm text-g60 max-w-2xl">
            Imagens de fundo dos slides do carrossel
            <strong className="text-onix-900"> @sindicompanybr</strong>. Cada
            slot é mapeado pra um slide específico em sequência: o slot{" "}
            <strong>1 vai pro slide 2</strong>, o <strong>2 pro slide 3</strong>,
            o <strong>3 pro slide 4</strong>, e assim por diante. Slide 1 (capa)
            usa a foto IA. As imagens mantêm a cor original e ficam coladas
            no canto inferior direito/esquerdo do slide (alternando por
            paridade). Suporta JPG, PNG, WebP e SVG. Máx 10MB cada.
          </p>
        </header>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {Array.from({ length: ICON_CARROSSEL_MAX_SLOTS }, (_, i) => i + 1).map(
            (slot) => (
              <IconCarrosselSlot
                key={slot}
                slot={slot}
                initialUrl={urls[slot - 1]}
              />
            ),
          )}
        </div>

        <div className="mt-8 text-xs text-g60">
          <strong className="text-onix-900">Como o engine usa:</strong> baixa
          todas as imagens disponíveis em ordem de slot e cicla pelo índice
          do slide (slide 2 → slot 1, slide 3 → slot 2, …). Slots vazios são
          pulados. SVG é recomendado pra escalar sem perda em 4K.
        </div>
      </main>
    </DashboardShell>
  );
}
