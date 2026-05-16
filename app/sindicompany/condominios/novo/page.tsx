import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { DashboardShell } from "../../shell";
import { criarCondominioAction } from "../actions";

const inputCls =
  "block w-full rounded-md border border-onix-100 bg-white px-3 py-2 text-sm text-onix-900 focus:outline-none focus:ring-2 focus:ring-mint-300";

export default async function NovoCondominioPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) redirect("/sindicompany/login");

  const sp = await searchParams;
  const error = typeof sp.error === "string" ? sp.error : "";

  return (
    <DashboardShell>
      <main className="max-w-xl mx-auto px-6 py-12">
        <Link
          href="/sindicompany/condominios"
          className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
        >
          ← Voltar para condomínios
        </Link>

        <header className="mb-8">
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
            Condomínios
          </div>
          <h1 className="text-3xl font-bold text-onix-900">Novo condomínio</h1>
          <p className="text-sm text-g60 mt-2">
            Digite o nome do condomínio. Depois você completa síndico, gestor,
            logos e contatos na tela de edição.
          </p>
        </header>

        {error && (
          <div className="mb-5 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-900">
            {error}
          </div>
        )}

        <form action={criarCondominioAction} className="space-y-5">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-onix-900">
              Nome do condomínio
            </label>
            <input
              type="text"
              name="nome"
              required
              maxLength={160}
              placeholder="Ex: Residencial Jardim das Flores"
              className={inputCls}
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              className="rounded-lg bg-onix-900 text-white px-5 py-2.5 font-medium hover:bg-onix-800"
            >
              Criar e cadastrar →
            </button>
            <Link
              href="/sindicompany/condominios"
              className="rounded-lg border border-onix-100 px-5 py-2.5 font-medium hover:bg-onix-50"
            >
              Cancelar
            </Link>
          </div>
        </form>
      </main>
    </DashboardShell>
  );
}
