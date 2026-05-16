import { cookies } from "next/headers";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { getCarrossel } from "@/lib/sindicompany/carrosseis";
import { DashboardShell } from "../../../shell";
import { CarrosselFotoUpload } from "../../foto-upload";
import { SlideFotoUpload } from "../../slide-foto-upload";
import { finalizarCarrosselAction } from "../../actions";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function FotoCapaPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  const { id } = await params;
  const carrossel = await getCarrossel(id);
  if (!carrossel) notFound();

  const idx = carrossel.copy_selected ?? 0;
  const copy = carrossel.copy_options?.[idx];
  const slide1 = copy?.slides?.[0];

  return (
    <DashboardShell>
      <main className="max-w-3xl mx-auto px-6 py-12">
        <Link
          href={`/sindicompany/carrossel/${carrossel.id}/copy`}
          className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
        >
          ← Trocar copy
        </Link>

        <header className="mb-8">
          <Stepper step={3} />
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2 mt-6">
            Etapa 3 · Foto da capa
          </div>
          <h1 className="text-3xl font-bold text-onix-900">
            Escolha a foto que vai abrir o carrossel
          </h1>
          <p className="text-sm text-g60 mt-2 max-w-xl">
            Faça upload de uma foto sua ou peça pra IA gerar uma com base na
            copy que você escolheu. A foto fica no slide 1 como capa.
          </p>
        </header>

        {slide1 && (
          <section className="rounded-xl border border-mint-100 bg-mint-50 px-5 py-4 mb-6">
            <div className="text-[10px] uppercase tracking-[0.24em] text-mint-700 font-semibold mb-1">
              Copy escolhida · Capa
            </div>
            <div className="text-base font-semibold text-onix-900">
              {slide1.titulo || "(sem título)"}
            </div>
            {slide1.body && (
              <div className="text-sm text-onix-800 mt-1">{slide1.body}</div>
            )}
          </section>
        )}

        <section className="rounded-xl border border-onix-100 bg-white p-6 mb-6">
          <h2 className="text-sm font-semibold text-onix-900 mb-4">
            Foto da capa
          </h2>
          <CarrosselFotoUpload
            carrosselId={carrossel.id}
            initialUrl={carrossel.foto_capa_url ?? undefined}
          />
        </section>

        <section className="rounded-xl border border-onix-100 bg-white p-6 mb-6">
          <h2 className="text-sm font-semibold text-onix-900 mb-1">
            Fotos por slide (opcional)
          </h2>
          <p className="text-xs text-g60 mb-4">
            Suba uma foto pra cada slide se quiser substituir o fundo padrão
            (cor + pattern). Slides sem foto continuam com o tema da marca.
          </p>
          <div className="space-y-2">
            {Array.from(
              { length: Math.max(0, (carrossel.n_slides ?? 6) - 1) },
              (_, i) => i + 1,
            ).map((slideIdx) => (
              <SlideFotoUpload
                key={slideIdx}
                carrosselId={carrossel.id}
                slideIdx={slideIdx}
                initialUrl={carrossel.slide_fotos?.[slideIdx] ?? null}
              />
            ))}
          </div>
        </section>

        <form action={finalizarCarrosselAction.bind(null, carrossel.id)}>
          <div className="flex gap-3 items-center">
            <button
              type="submit"
              className="rounded-lg bg-onix-900 text-white px-5 py-2.5 font-medium hover:bg-onix-800"
            >
              Gerar carrossel →
            </button>
            <span className="text-xs text-g60">
              A engine vai compor os {carrossel.n_slides} slides em PNG. Demora
              1-3 min em background.
            </span>
          </div>
        </form>
      </main>
    </DashboardShell>
  );
}

function Stepper({ step }: { step: 1 | 2 | 3 }) {
  const items = [
    { n: 1, label: "Briefing" },
    { n: 2, label: "Escolher copy" },
    { n: 3, label: "Foto da capa" },
  ];
  return (
    <nav className="flex items-center gap-2 text-xs">
      {items.map((it, i) => {
        const active = it.n === step;
        const done = it.n < step;
        return (
          <div key={it.n} className="flex items-center gap-2">
            <span
              className={`w-6 h-6 inline-flex items-center justify-center rounded-full font-semibold ${
                active
                  ? "bg-onix-900 text-white"
                  : done
                    ? "bg-mint-100 text-mint-700"
                    : "bg-onix-50 text-g60"
              }`}
            >
              {done ? "✓" : it.n}
            </span>
            <span className={active ? "text-onix-900 font-medium" : "text-g60"}>
              {it.label}
            </span>
            {i < items.length - 1 && <span className="text-g60">›</span>}
          </div>
        );
      })}
    </nav>
  );
}
