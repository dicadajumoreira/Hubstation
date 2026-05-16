import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  listCarrosseis,
  type Carrossel,
} from "@/lib/sindicompany/carrosseis";
import { DashboardShell } from "../shell";
import { CarrosselRowActions } from "./row-actions";

const STATUS_LABELS: Record<Carrossel["status"], string> = {
  rascunho: "Rascunho",
  em_producao: "Em produção",
  publicada: "Pronto",
  erro: "Erro",
};

const STATUS_CLASSES: Record<Carrossel["status"], string> = {
  rascunho: "bg-onix-50 text-onix-800",
  em_producao: "bg-mint-50 text-mint-700",
  publicada: "bg-mint-100 text-mint-700",
  erro: "bg-red-50 text-red-800",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default async function CarrosseisPage() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  let carrosseis: Carrossel[] = [];
  let dbError: string | null = null;
  try {
    carrosseis = await listCarrosseis();
  } catch (e) {
    dbError =
      "Tabela 'carrosseis' não existe ainda. Rode a migration 20260520_carrosseis.sql no Supabase.";
  }

  return (
    <DashboardShell>
      <main className="max-w-6xl mx-auto px-6 py-12">
        <header className="flex items-start justify-between mb-10">
          <div>
            <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
              Carrosséis · Instagram
            </div>
            <h1 className="text-4xl font-bold text-onix-900 leading-tight">
              Carrosséis
            </h1>
            <p className="text-sm text-g60 mt-2 max-w-md">
              Gere posts em formato carrossel 4K (3072×3839, 4:5) pra Instagram,
              com identidade visual da marca aplicada automaticamente.
            </p>
          </div>
          <Link
            href="/sindicompany/carrossel/novo"
            className="inline-flex items-center px-4 py-2.5 rounded-lg bg-onix-900 text-white font-medium hover:bg-onix-800 text-sm"
          >
            + Novo carrossel
          </Link>
        </header>

        {dbError && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900 mb-6">
            {dbError}
          </div>
        )}

        {!dbError && carrosseis.length === 0 && (
          <div className="rounded-xl border border-onix-100 bg-white p-10 text-center">
            <p className="text-onix-900 font-medium mb-2">
              Nenhum carrossel ainda
            </p>
            <p className="text-sm text-g60 mb-5 max-w-md mx-auto">
              Comece criando o primeiro carrossel da sua conta. Você escolhe o
              tema, formato e foto da capa, e a engine gera os PNGs em 4K com
              identidade Sindicompany.
            </p>
            <Link
              href="/sindicompany/carrossel/novo"
              className="inline-flex items-center px-4 py-2.5 rounded-lg bg-onix-900 text-white font-medium hover:bg-onix-800 text-sm"
            >
              Criar primeiro carrossel
            </Link>
          </div>
        )}

        {carrosseis.length > 0 && (
          <div className="rounded-xl border border-onix-100 bg-white overflow-x-auto">
            <table className="w-full text-sm min-w-[840px]">
              <thead className="bg-onix-50">
                <tr>
                  <th className="text-left font-semibold text-onix-900 px-5 py-3">
                    Marca
                  </th>
                  <th className="text-left font-semibold text-onix-900 px-5 py-3">
                    Título
                  </th>
                  <th className="text-left font-semibold text-onix-900 px-5 py-3">
                    Tema
                  </th>
                  <th className="text-left font-semibold text-onix-900 px-5 py-3">
                    Formato
                  </th>
                  <th className="text-left font-semibold text-onix-900 px-5 py-3">
                    Slides
                  </th>
                  <th className="text-left font-semibold text-onix-900 px-5 py-3">
                    Status
                  </th>
                  <th className="text-left font-semibold text-onix-900 px-5 py-3">
                    Criado
                  </th>
                  <th className="text-right font-semibold text-onix-900 px-5 py-3">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody>
                {carrosseis.map((c) => (
                  <tr
                    key={c.id}
                    className="border-t border-onix-100 hover:bg-onix-50/50"
                  >
                    <td className="px-5 py-3">
                      <span className="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-onix-100 text-onix-800">
                        {c.brand === "bysindicompany"
                          ? "@bysindicompany"
                          : c.brand === "consvictabr"
                            ? "@consvictabr"
                            : "@sindicompanybr"}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <Link
                        href={`/sindicompany/carrossel/${c.id}`}
                        className="text-onix-900 font-medium hover:underline"
                      >
                        {c.titulo}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-g60">{c.tema ?? "—"}</td>
                    <td className="px-5 py-3 text-g60">{c.formato ?? "—"}</td>
                    <td className="px-5 py-3 text-g60">{c.n_slides ?? 6}</td>
                    <td className="px-5 py-3">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded text-xs font-semibold ${STATUS_CLASSES[c.status]}`}
                      >
                        {STATUS_LABELS[c.status]}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-g60 text-xs">
                      {formatDate(c.created_at)}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <div className="inline-flex justify-end">
                        <CarrosselRowActions id={c.id} titulo={c.titulo} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </DashboardShell>
  );
}
