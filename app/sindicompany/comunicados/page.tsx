import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { listComunicados, type Comunicado } from "@/lib/sindicompany/comunicados";
import { DashboardShell } from "../shell";

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
  } catch {
    return iso;
  }
}

export default async function ComunicadosPage() {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) redirect("/sindicompany/login");

  let comunicados: Comunicado[] = [];
  let erro: string | null = null;
  try {
    comunicados = await listComunicados();
  } catch (e) {
    erro = e instanceof Error ? e.message : String(e);
  }

  return (
    <DashboardShell>
      <main className="max-w-5xl mx-auto px-6 py-12">
        <Link href="/sindicompany/dashboard" className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block">
          ← Voltar
        </Link>
        <header className="mb-10 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">Comunicados</div>
            <h1 className="text-3xl font-bold text-onix-900">Comunicados aos moradores</h1>
            <p className="text-sm text-g60 mt-2 max-w-xl">
              Avisos do condomínio gerados em dois formatos: A4 (para impressão / mural) e Celular (imagem para postar no WhatsApp / Instagram).
            </p>
          </div>
          <Link href="/sindicompany/comunicados/novo" className="inline-flex items-center px-4 py-2.5 rounded-lg bg-onix-900 text-white font-medium hover:bg-onix-800 text-sm whitespace-nowrap">
            + Novo comunicado
          </Link>
        </header>

        {erro && (
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <strong>Banco indisponível.</strong> {erro}{" "}
            <span className="block mt-1 text-amber-800">Rode a migration 20260537 no Supabase.</span>
          </div>
        )}

        <section className="bg-white rounded-xl border border-onix-100 overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="border-b border-onix-100 text-left">
                <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Título</th>
                <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Condomínio</th>
                <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider text-mint-700">Criado</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {comunicados.length === 0 && !erro && (
                <tr><td colSpan={4} className="px-6 py-8 text-center text-g60 italic">Nenhum comunicado ainda.</td></tr>
              )}
              {comunicados.map((c) => (
                <tr key={c.id} className="border-b border-onix-100 last:border-0">
                  <td className="px-6 py-4 font-medium text-onix-900">
                    {c.titulo}
                    {c.subtitulo && <span className="text-g60 font-normal"> · {c.subtitulo}</span>}
                  </td>
                  <td className="px-6 py-4 text-onix-800">{c.condominio}</td>
                  <td className="px-6 py-4 text-g60">{fmtDate(c.created_at)}</td>
                  <td className="px-6 py-4 text-right">
                    <Link href={`/sindicompany/comunicados/${c.id}`} className="text-mint-700 font-medium hover:underline">
                      Abrir →
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
