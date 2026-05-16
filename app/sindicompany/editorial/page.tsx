import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  listEditoriais,
  editorialEstaPronto,
  formatMesAno,
  type Editorial,
} from "@/lib/sindicompany/editoriais";
import { DashboardShell } from "../shell";

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

async function safeList(): Promise<{ items: Editorial[]; error: string | null }> {
  try {
    return { items: await listEditoriais(), error: null };
  } catch (e) {
    return { items: [], error: e instanceof Error ? e.message : String(e) };
  }
}

/** Gera os próximos 6 meses começando pelo atual, pra a editora ter
 *  uma lista de slots a preencher mesmo sem editorial criado ainda. */
function nextMonths(count = 6): Array<{ mes: number; ano: number }> {
  const out: Array<{ mes: number; ano: number }> = [];
  const now = new Date();
  let mes = now.getMonth() + 1;
  let ano = now.getFullYear();
  for (let i = 0; i < count; i++) {
    out.push({ mes, ano });
    mes += 1;
    if (mes > 12) {
      mes = 1;
      ano += 1;
    }
  }
  return out;
}

export default async function EditorialListPage() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  const { items, error } = await safeList();
  const byKey = new Map(items.map((e) => [`${e.mes}-${e.ano}`, e]));
  const proximos = nextMonths(6);

  return (
    <DashboardShell>
    <main className="max-w-4xl mx-auto px-6 py-12">
      <Link
        href="/sindicompany/dashboard"
        className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
      >
        ← Voltar
      </Link>

      <header className="mb-10">
        <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
          Editorial mensal
        </div>
        <h1 className="text-3xl font-bold text-onix-900">Decisões editoriais do mês</h1>
        <p className="text-sm text-g60 mt-2 max-w-xl">
          O que vale para todas as revistas do mês: matéria de capa, foto,
          receita e temas sugeridos das cartas. Decida uma vez aqui e a equipe
          só preenche por condomínio depois.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <strong>Banco indisponível.</strong> {error}
        </div>
      )}

      <section className="bg-white rounded-xl border border-onix-100">
        <h2 className="px-6 py-3 border-b border-onix-100 text-xs uppercase tracking-wider font-semibold text-mint-700">
          Próximas edições
        </h2>
        <div className="overflow-x-auto">
        <table className="w-full text-sm min-w-[640px]">
          <thead className="bg-onix-50">
            <tr className="text-left">
              <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Edição</th>
              <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Status</th>
              <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Matéria de capa</th>
              <th className="px-6 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {proximos.map(({ mes, ano }) => {
              const meta = byKey.get(`${mes}-${ano}`);
              const pronto = editorialEstaPronto(meta ?? null);
              const slug = formatMesAno(mes, ano);
              return (
                <tr key={slug} className="border-t border-onix-100">
                  <td className="px-6 py-4 font-medium text-onix-900">
                    {MESES[mes - 1]} <span className="text-g60 tabular-nums">/ {ano}</span>
                  </td>
                  <td className="px-6 py-4">
                    {pronto ? (
                      <span className="inline-block px-2.5 py-0.5 rounded text-xs font-semibold bg-mint-50 text-mint-700">
                        Pronto
                      </span>
                    ) : meta ? (
                      <span className="inline-block px-2.5 py-0.5 rounded text-xs font-semibold bg-onix-50 text-onix-800">
                        Em rascunho
                      </span>
                    ) : (
                      <span className="inline-block px-2.5 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-800">
                        Vazio
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-onix-800 max-w-md truncate">
                    {meta?.materia_capa_titulo ?? <span className="text-g60 italic">—</span>}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      href={`/sindicompany/editorial/${slug}`}
                      className="text-mint-700 font-medium hover:underline"
                    >
                      {meta ? "Editar" : "Definir"} →
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </section>

      {items.filter((e) => !proximos.some((p) => p.mes === e.mes && p.ano === e.ano)).length > 0 && (
        <section className="bg-white rounded-xl border border-onix-100 mt-8">
          <h2 className="px-6 py-3 border-b border-onix-100 text-xs uppercase tracking-wider font-semibold text-mint-700">
            Edições anteriores
          </h2>
          <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]">
            <tbody>
              {items
                .filter((e) => !proximos.some((p) => p.mes === e.mes && p.ano === e.ano))
                .map((e) => {
                  const slug = formatMesAno(e.mes, e.ano);
                  return (
                    <tr key={slug} className="border-t border-onix-100 first:border-0">
                      <td className="px-6 py-4 font-medium text-onix-900">
                        {MESES[e.mes - 1]} <span className="text-g60 tabular-nums">/ {e.ano}</span>
                      </td>
                      <td className="px-6 py-4 text-onix-800 max-w-md truncate">
                        {e.materia_capa_titulo ?? <span className="text-g60 italic">—</span>}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href={`/sindicompany/editorial/${slug}`}
                          className="text-mint-700 font-medium hover:underline"
                        >
                          Editar →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
          </div>
        </section>
      )}
    </main>
    </DashboardShell>
  );
}
