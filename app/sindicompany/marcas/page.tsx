import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { listMarcas, type Marca } from "@/lib/sindicompany/marcas-db";
import { DashboardShell } from "../shell";

export default async function MarcasPage() {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) {
    redirect("/sindicompany/login");
  }

  let marcas: Marca[] = [];
  let erro: string | null = null;
  try {
    marcas = await listMarcas();
  } catch (e) {
    erro = e instanceof Error ? e.message : String(e);
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
        <header className="mb-10 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
              Marcas
            </div>
            <h1 className="text-3xl font-bold text-onix-900">Marcas</h1>
            <p className="text-sm text-g60 mt-2 max-w-xl">
              Cada marca tem persona (voz/copy), temas e identidade próprios.
              Marca ativa aparece no seletor do /carrossel/novo e gera copy no
              tom da persona dela.
            </p>
          </div>
          <Link
            href="/sindicompany/marcas/novo"
            className="inline-flex items-center px-4 py-2.5 rounded-lg bg-onix-900 text-white font-medium hover:bg-onix-800 text-sm whitespace-nowrap"
          >
            + Nova marca
          </Link>
        </header>

        {erro && (
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <strong>Banco indisponível.</strong> {erro}{" "}
            <span className="block mt-1 text-amber-800">
              Rode a migration 20260541 no Supabase.
            </span>
          </div>
        )}

        <section className="bg-white rounded-xl border border-onix-100 overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="border-b border-onix-100 text-left">
                <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Marca</th>
                <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Handle</th>
                <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Nicho</th>
                <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Temas</th>
                <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Status</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {marcas.length === 0 && !erro && (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-g60 italic">
                    Nenhuma marca ainda.
                  </td>
                </tr>
              )}
              {marcas.map((m) => (
                <tr key={m.slug} className="border-b border-onix-100 last:border-0">
                  <td className="px-6 py-4 font-medium text-onix-900">
                    {m.nome}
                    <span className="text-g60 font-normal"> · {m.slug}</span>
                  </td>
                  <td className="px-6 py-4 text-onix-800">{m.handle}</td>
                  <td className="px-6 py-4 text-g60">{m.nicho ?? "—"}</td>
                  <td className="px-6 py-4 text-g60">{m.temasSugeridos?.length ?? 0}</td>
                  <td className="px-6 py-4">
                    {m.ativo ? (
                      <span className="text-xs font-semibold text-mint-700">Ativa</span>
                    ) : (
                      <span className="text-xs text-g60">Inativa</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      href={`/sindicompany/marcas/${m.slug}`}
                      className="text-mint-700 font-medium hover:underline"
                    >
                      Editar →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </DashboardShell>
  );
}
