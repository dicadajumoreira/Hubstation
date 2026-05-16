import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { CONDOMINIOS, slugifyCondo } from "@/lib/sindicompany/condominios";
import { listCondoMetas, type CondoMeta } from "@/lib/sindicompany/condominios-db";
import { DashboardShell } from "../shell";

export default async function BoasVindasIndexPage() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) redirect("/sindicompany/login");

  let metas = new Map<string, CondoMeta>();
  try {
    metas = new Map((await listCondoMetas()).map((m) => [m.nome, m]));
  } catch {
    // segue com metas vazio
  }

  const nomes = Array.from(
    new Set<string>([...CONDOMINIOS, ...Array.from(metas.keys())]),
  ).sort((a, b) => a.localeCompare(b, "pt-BR", { sensitivity: "base" }));

  return (
    <DashboardShell>
      <main className="max-w-4xl mx-auto px-6 py-12">
        <Link
          href="/sindicompany/dashboard"
          className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
        >
          ← Voltar
        </Link>

        <header className="mb-8">
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
            Revista de Boas-Vindas
          </div>
          <h1 className="text-3xl font-bold text-onix-900">
            Revista de Boas-Vindas
          </h1>
          <p className="text-sm text-g60 mt-2 max-w-xl">
            Escolha o condomínio pra abrir a revista de boas-vindas (3 páginas,
            pronta pra imprimir/salvar em PDF). Ela é montada com os dados do
            cadastro do condomínio — síndico, gestor, equipe de atendimento e
            comunidade.
          </p>
        </header>

        <section className="bg-white rounded-xl border border-onix-100 overflow-x-auto">
          <table className="w-full text-sm min-w-[480px]">
            <thead>
              <tr className="border-b border-onix-100 text-left">
                <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">
                  Condomínio
                </th>
                <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">
                  Síndico(a)
                </th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {nomes.map((nome) => {
                const meta = metas.get(nome);
                const slug = slugifyCondo(nome);
                return (
                  <tr key={nome} className="border-b border-onix-100 last:border-0">
                    <td className="px-6 py-4 font-medium text-onix-900">{nome}</td>
                    <td className="px-6 py-4 text-onix-800">
                      {meta?.sindico_nome ?? (
                        <span className="text-g60 italic">não cadastrado</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/sindicompany/condominios/${slug}/boas-vindas`}
                        className="text-mint-700 font-medium hover:underline"
                      >
                        Abrir revista →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      </main>
    </DashboardShell>
  );
}
