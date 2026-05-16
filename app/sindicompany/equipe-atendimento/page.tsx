import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  getFotoMembroEquipeUrl,
  listEquipeAtendimentoGlobal,
  type MembroEquipe,
} from "@/lib/sindicompany/equipe-atendimento";
import { DashboardShell } from "../shell";
import { adicionarMembroAction, removerMembroAction } from "./actions";

export default async function EquipeAtendimentoPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) redirect("/sindicompany/login");
  const sp = await searchParams;
  const error = typeof sp.error === "string" ? sp.error : "";
  const added = sp.added === "1";
  const removed = sp.removed === "1";

  let equipe: MembroEquipe[] = [];
  let dbError: string | null = null;
  try {
    equipe = await listEquipeAtendimentoGlobal();
  } catch (e) {
    dbError = e instanceof Error ? e.message : String(e);
  }

  return (
    <DashboardShell>
      <main className="max-w-4xl mx-auto px-6 py-12">
        <Link href="/sindicompany/condominios" className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block">
          ← Voltar para condomínios
        </Link>
        <header className="mb-10">
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
            Condomínios · Equipe
          </div>
          <h1 className="text-3xl font-bold text-onix-900">Equipe de Atendimento</h1>
          <p className="text-sm text-g60 mt-2 max-w-2xl">
            Equipe compartilhada que atende todos os condomínios. Aparece na Revista Mensal
            logo após o convite da comunidade, e também na Revista de Boas-Vindas.
          </p>
        </header>

        {error && (
          <div className="mb-5 rounded-lg bg-rose-50 border border-rose-200 px-4 py-3 text-sm text-rose-900">{error}</div>
        )}
        {dbError && (
          <div className="mb-5 rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900">
            <strong>Banco indisponível.</strong> {dbError}{" "}
            <span className="block mt-1">Rode a migration 20260539 no Supabase.</span>
          </div>
        )}
        {added && !error && (
          <div className="mb-5 rounded-lg bg-mint-50 border border-mint-100 px-4 py-3 text-sm text-mint-700">
            Membro adicionado à equipe.
          </div>
        )}
        {removed && !error && (
          <div className="mb-5 rounded-lg bg-mint-50 border border-mint-100 px-4 py-3 text-sm text-mint-700">
            Membro removido da equipe.
          </div>
        )}

        <section className="bg-white rounded-xl border border-onix-100 overflow-hidden mb-10">
          <div className="px-6 py-3 border-b border-onix-100 bg-onix-50">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
              Membros da equipe ({equipe.length})
            </h2>
          </div>
          {equipe.length === 0 ? (
            <p className="px-6 py-8 text-sm text-g60 italic text-center">
              Nenhum membro cadastrado. Adicione abaixo.
            </p>
          ) : (
            <ul className="divide-y divide-onix-100">
              {equipe.map((m) => {
                const fotoUrl = m.foto_path ? getFotoMembroEquipeUrl(m.foto_path) : null;
                return (
                  <li key={m.id} className="flex items-center gap-4 px-6 py-4">
                    {fotoUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={fotoUrl} alt={m.nome} className="w-12 h-12 rounded-full object-cover bg-onix-100" />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-onix-100" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-onix-900 truncate">{m.nome}</div>
                      <div className="text-xs text-g60 truncate">{m.cargo}</div>
                    </div>
                    <form action={removerMembroAction}>
                      <input type="hidden" name="id" value={m.id} />
                      <button
                        type="submit"
                        className="text-xs text-rose-600 hover:underline"
                      >
                        Remover
                      </button>
                    </form>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="bg-white rounded-xl border border-onix-100 p-6">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700 mb-4">
            Adicionar membro
          </h2>
          <form action={adicionarMembroAction} encType="multipart/form-data" className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-onix-900 mb-1">Nome</label>
              <input name="nome" required maxLength={120} className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-onix-900 mb-1">Cargo</label>
              <input name="cargo" required maxLength={120} placeholder="Ex.: Gestão de Pessoas" className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-onix-900 mb-1">
                Foto <span className="text-g60 font-normal">(opcional, JPG/PNG/WebP, até 5MB)</span>
              </label>
              <input name="foto" type="file" accept="image/jpeg,image/png,image/webp" className="block text-sm" />
            </div>
            <button
              type="submit"
              className="inline-flex items-center px-5 py-2.5 rounded-lg bg-onix-900 text-white font-medium hover:bg-onix-800 text-sm"
            >
              Adicionar à equipe
            </button>
          </form>
        </section>
      </main>
    </DashboardShell>
  );
}
