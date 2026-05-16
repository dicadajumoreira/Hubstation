import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { CONDOMINIOS, slugifyCondo } from "@/lib/sindicompany/condominios";
import { listCondoMetas, type CondoMeta } from "@/lib/sindicompany/condominios-db";
import { DashboardShell } from "../shell";

async function safeListMetas(): Promise<{ metas: Map<string, CondoMeta>; error: string | null }> {
  try {
    const list = await listCondoMetas();
    const map = new Map(list.map((m) => [m.nome, m]));
    return { metas: map, error: null };
  } catch (e) {
    return { metas: new Map(), error: e instanceof Error ? e.message : String(e) };
  }
}

export default async function CondominiosPage() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  const { metas, error } = await safeListMetas();

  // Lista exibida = lista canonica estatica + qualquer condominio
  // cadastrado so no banco (criado pelo botao 'Novo condominio'),
  // tudo em ordem alfabetica pt-BR.
  const todosNomes = Array.from(
    new Set<string>([...CONDOMINIOS, ...Array.from(metas.keys())]),
  ).sort((a, b) => a.localeCompare(b, "pt-BR", { sensitivity: "base" }));

  return (
    <DashboardShell>
    <main className="max-w-5xl mx-auto px-6 py-12">
      <Link
        href="/sindicompany/dashboard"
        className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
      >
        ← Voltar
      </Link>

      <header className="mb-10 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
            Condomínios
          </div>
          <h1 className="text-3xl font-bold text-onix-900">Cadastro de condomínios</h1>
          <p className="text-sm text-g60 mt-2 max-w-xl">
            Síndico(a), Gestor(a) de Atendimento, logotipos, contatos e
            comunidade de cada condomínio ficam salvos aqui e são aplicados em
            todas as edições da revista.
          </p>
        </div>
        <Link
          href="/sindicompany/condominios/novo"
          className="inline-flex items-center px-4 py-2.5 rounded-lg bg-onix-900 text-white font-medium hover:bg-onix-800 text-sm whitespace-nowrap"
        >
          + Novo condomínio
        </Link>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <strong>Banco indisponível.</strong> {error}
        </div>
      )}

      <section className="bg-white rounded-xl border border-onix-100 overflow-x-auto">
        <table className="w-full text-sm min-w-[640px]">
          <thead>
            <tr className="border-b border-onix-100 text-left">
              <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">
                Condomínio
              </th>
              <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">
                Síndico(a)
              </th>
              <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">
                Logo
              </th>
              <th className="px-6 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {todosNomes.map((nome) => {
              const meta = metas.get(nome);
              const slug = slugifyCondo(nome);
              const sindicoStatus = meta?.sindico_nome
                ? meta.sindico_nome
                : <span className="text-g60 italic">não cadastrado</span>;
              const logoStatus = meta?.logo_url
                ? <span className="text-mint-700">cadastrado</span>
                : <span className="text-g60 italic">não cadastrado</span>;

              return (
                <tr key={nome} className="border-b border-onix-100 last:border-0">
                  <td className="px-6 py-4 font-medium text-onix-900">{nome}</td>
                  <td className="px-6 py-4 text-onix-800">{sindicoStatus}</td>
                  <td className="px-6 py-4 text-onix-800">{logoStatus}</td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      href={`/sindicompany/condominios/${slug}`}
                      className="text-mint-700 font-medium hover:underline"
                    >
                      {meta ? "Editar" : "Cadastrar"} →
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
