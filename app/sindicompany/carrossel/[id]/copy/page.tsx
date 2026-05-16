import { cookies } from "next/headers";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { getCarrossel, type CarrosselCopy } from "@/lib/sindicompany/carrosseis";
import { DashboardShell } from "../../../shell";
import {
  escolherCopyAction,
  regenerarCopiesAction,
} from "../../actions";
import { AutoGenerateCopies } from "./auto-generate";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const ANGULOS = ["Emocional", "Informativa", "Provocativa"];

export default async function EscolherCopyPage({
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

  const copies = carrossel.copy_options ?? [];

  return (
    <DashboardShell>
      <main className="max-w-6xl mx-auto px-6 py-12">
        <Link
          href="/sindicompany/carrossel"
          className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
        >
          ← Voltar
        </Link>

        <header className="mb-8 flex items-start justify-between gap-4">
          <div>
            <Stepper step={2} />
            <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2 mt-6">
              Etapa 2 · Escolher copy
            </div>
            <h1 className="text-3xl font-bold text-onix-900">
              Qual versão você quer publicar?
            </h1>
            <p className="text-sm text-g60 mt-2 max-w-2xl">
              A IA gerou 3 ângulos diferentes pro mesmo briefing. Leia os
              slides, compare a legenda, e escolha a que mais combina com o tom
              da marca.
            </p>
          </div>
          {copies.length > 0 && (
            <form
              action={regenerarCopiesAction.bind(null, carrossel.id)}
              className="shrink-0 mt-2"
            >
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 rounded-lg border border-onix-200 bg-white hover:bg-onix-50 text-onix-900 text-sm font-medium px-3 py-2"
              >
                ↻ Gerar 3 opções novas
              </button>
            </form>
          )}
        </header>

        {copies.length === 0 ? (
          <AutoGenerateCopies carrosselId={carrossel.id} />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {copies.map((copy, idx) => (
              <CopyCard
                key={idx}
                copy={copy}
                idx={idx}
                carrosselId={carrossel.id}
              />
            ))}
          </div>
        )}
      </main>
    </DashboardShell>
  );
}

function CopyCard({
  copy,
  idx,
  carrosselId,
}: {
  copy: CarrosselCopy;
  idx: number;
  carrosselId: string;
}) {
  const angulo = ANGULOS[idx] ?? `Versão ${idx + 1}`;
  return (
    <article className="flex flex-col rounded-xl border border-onix-100 bg-white overflow-hidden">
      <header className="px-5 py-3 border-b border-onix-100 bg-onix-50">
        <div className="text-[10px] uppercase tracking-[0.24em] text-mint-700 font-semibold">
          Versão {String.fromCharCode(65 + idx)}
        </div>
        <div className="text-sm font-semibold text-onix-900 mt-0.5">{angulo}</div>
      </header>

      <div className="flex-1 px-5 py-4 space-y-3">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-g60 font-semibold mb-1.5">
            Slides ({copy.slides.length})
          </div>
          <ol className="space-y-2 text-sm">
            {copy.slides.map((s, i) => (
              <li
                key={i}
                className="rounded-md bg-onix-50 px-3 py-2 border border-onix-100"
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="inline-block bg-onix-900 text-white text-[10px] font-semibold px-1.5 py-0.5 rounded">
                    {i + 1}
                  </span>
                  <span className="text-[10px] text-g60 uppercase tracking-wider">
                    {s.tipo || "texto"}
                  </span>
                </div>
                {s.titulo && (
                  <div className="text-sm font-semibold text-onix-900 leading-snug">
                    {s.titulo}
                  </div>
                )}
                {s.body && (
                  <div className="text-xs text-onix-800 mt-0.5 leading-relaxed">
                    {s.body}
                  </div>
                )}
              </li>
            ))}
          </ol>
        </div>

        {copy.legenda && (
          <div>
            <div className="text-[10px] uppercase tracking-wider text-g60 font-semibold mb-1.5">
              Legenda
            </div>
            <p className="text-xs text-onix-800 whitespace-pre-wrap leading-relaxed bg-mint-50 border border-mint-100 rounded-md px-3 py-2">
              {copy.legenda}
            </p>
          </div>
        )}
      </div>

      <footer className="px-5 py-3 border-t border-onix-100">
        <form action={escolherCopyAction.bind(null, carrosselId, idx)}>
          <button
            type="submit"
            className="w-full rounded-lg bg-onix-900 hover:bg-onix-800 text-white text-sm font-medium py-2"
          >
            Escolher esta →
          </button>
        </form>
      </footer>
    </article>
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
