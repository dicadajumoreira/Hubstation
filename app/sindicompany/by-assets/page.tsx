import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  ICON_CARROSSEL_MAX_SLOTS,
  ICON_MAX_SLOTS,
  LOGO_MAX_SLOTS,
  PATTERN_MAX_SLOTS,
  listByIconCarrosselUrls,
  listByIconUrls,
  listByLogoUrls,
  listByPatternUrls,
} from "@/lib/sindicompany/condominios-db";
import {
  getByIconCarrosselUploadIntent,
  getByIconUploadIntent,
  getByLogoUploadIntent,
  getByPatternUploadIntent,
} from "../revista/nova/upload-actions";
import { ByAssetSlot } from "../by-assets-slot";
import { CopiarAssetsButton } from "./copiar-assets-button";
import { DashboardShell } from "../shell";

export default async function ByAssetsPage() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  const safe = async <T,>(fn: () => Promise<T>, fallback: T): Promise<T> => {
    try {
      return await fn();
    } catch {
      return fallback;
    }
  };

  const patterns = await safe(
    listByPatternUrls,
    Array(PATTERN_MAX_SLOTS).fill(null) as (string | null)[],
  );
  const icons = await safe(
    listByIconUrls,
    Array(ICON_MAX_SLOTS).fill(null) as (string | null)[],
  );
  const fundos = await safe(
    listByIconCarrosselUrls,
    Array(ICON_CARROSSEL_MAX_SLOTS).fill(null) as (string | null)[],
  );
  const logos = await safe(
    listByLogoUrls,
    Array(LOGO_MAX_SLOTS).fill(null) as (string | null)[],
  );

  return (
    <DashboardShell>
      <main className="max-w-5xl mx-auto px-6 py-12 space-y-12">
        <Link
          href="/sindicompany/dashboard"
          className="text-sm text-g60 hover:text-onix-900 inline-block"
        >
          ← Voltar
        </Link>

        <header>
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
            Tema · Carrossel @bysindicompany
          </div>
          <h1 className="text-3xl font-bold text-onix-900 mb-2">
            Assets BySindicompany
          </h1>
          <p className="text-sm text-g60 max-w-2xl mb-4">
            Assets exclusivos dos carrosséis da marca{" "}
            <strong className="text-onix-900">@bysindicompany</strong>. A engine
            usa estes buckets (e não os do @sindicompanybr) quando o carrossel
            for criado com a marca BySindicompany. JPG, PNG, WebP e SVG. Máx
            10MB cada.
          </p>
          <CopiarAssetsButton />
        </header>

        <section>
          <h2 className="text-sm font-semibold text-onix-900 mb-1">Patterns</h2>
          <p className="text-xs text-g60 mb-4">
            Texturas de fundo dos slides (10% opacity). Até 20.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {Array.from({ length: PATTERN_MAX_SLOTS }, (_, i) => i + 1).map((s) => (
              <ByAssetSlot
                key={s}
                slot={s}
                label="Pattern"
                initialUrl={patterns[s - 1]}
                uploadIntent={getByPatternUploadIntent}
              />
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-onix-900 mb-1">Icons</h2>
          <p className="text-xs text-g60 mb-4">
            Biblioteca de ícones (slot 2 = capa, slot 6 = CTA). Até 20.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {Array.from({ length: ICON_MAX_SLOTS }, (_, i) => i + 1).map((s) => (
              <ByAssetSlot
                key={s}
                slot={s}
                label="Icon"
                initialUrl={icons[s - 1]}
                uploadIntent={getByIconUploadIntent}
              />
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-onix-900 mb-1">
            Fundo Carrossel
          </h2>
          <p className="text-xs text-g60 mb-4">
            Imagens de fundo dos slides: slot 1 → slide 2, slot 2 → slide 3, …
            Até 20.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {Array.from(
              { length: ICON_CARROSSEL_MAX_SLOTS },
              (_, i) => i + 1,
            ).map((s) => (
              <ByAssetSlot
                key={s}
                slot={s}
                label="Fundo"
                hint={`Slide ${s + 1}`}
                initialUrl={fundos[s - 1]}
                uploadIntent={getByIconCarrosselUploadIntent}
              />
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-onix-900 mb-1">Logotipos</h2>
          <p className="text-xs text-g60 mb-4">
            Variantes do logo BySindicompany (slot 5 = topo dos slides). Até 10.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {Array.from({ length: LOGO_MAX_SLOTS }, (_, i) => i + 1).map((s) => (
              <ByAssetSlot
                key={s}
                slot={s}
                label="Logo"
                aspect="wide"
                initialUrl={logos[s - 1]}
                uploadIntent={getByLogoUploadIntent}
              />
            ))}
          </div>
        </section>
      </main>
    </DashboardShell>
  );
}
