import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { CONDOMINIOS } from "@/lib/sindicompany/condominios";
import { listCondoMetas } from "@/lib/sindicompany/condominios-db";
import { DashboardShell } from "../../shell";
import { criarComunicadoAction } from "../actions";

export default async function NovoComunicadoPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) redirect("/sindicompany/login");
  const { error } = await searchParams;

  let nomes: string[] = [...CONDOMINIOS];
  try {
    const metas = await listCondoMetas();
    nomes = Array.from(new Set<string>([...CONDOMINIOS, ...metas.map((m) => m.nome)]));
  } catch {
    /* mantem a lista estatica */
  }
  nomes.sort((a, b) => a.localeCompare(b, "pt-BR", { sensitivity: "base" }));

  return (
    <DashboardShell>
      <main className="max-w-2xl mx-auto px-6 py-12">
        <Link href="/sindicompany/comunicados" className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block">
          ← Voltar
        </Link>
        <h1 className="text-2xl font-bold text-onix-900 mb-2">Novo comunicado</h1>
        <p className="text-sm text-g60 mb-8">
          Preencha o assunto e, se quiser, já escreva o texto. Você também pode deixar o texto vazio e escrever um briefing para gerar com IA na próxima tela. A ilustração do canto superior direito é enviada depois, na tela do comunicado.
        </p>

        {error && (
          <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>
        )}

        <form action={criarComunicadoAction} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-onix-900 mb-1">Condomínio</label>
            <select name="condominio" required className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm">
              <option value="">Selecione…</option>
              {nomes.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-onix-900 mb-1">Título do comunicado</label>
            <input name="titulo" required maxLength={90} placeholder="Ex.: Pets nas áreas comuns" className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-onix-900 mb-1">Subtítulo <span className="text-g60 font-normal">(opcional)</span></label>
            <input name="subtitulo" maxLength={90} placeholder="Ex.: Acesso ao condomínio" className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-onix-900 mb-1">Briefing para a IA <span className="text-g60 font-normal">(opcional)</span></label>
            <textarea name="briefing" rows={3} placeholder="Em poucas linhas, o que precisa ser comunicado. Ex.: pedir que os tutores recolham os dejetos e não deixem os pets soltos nas áreas comuns." className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-onix-900 mb-1">Texto do comunicado <span className="text-g60 font-normal">(opcional — pode gerar com IA depois)</span></label>
            <textarea name="corpo" rows={8} placeholder={"Prezados moradores,\n\n…"} className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm" />
            <p className="text-[11px] text-g60 mt-1">Dica: mantenha em torno de 150–190 palavras / 4-5 parágrafos curtos pra caber tanto no Story quanto no A4. (A IA já gera nesse tamanho.)</p>
          </div>
          <button type="submit" className="inline-flex items-center px-5 py-2.5 rounded-lg bg-onix-900 text-white font-medium hover:bg-onix-800 text-sm">
            Criar comunicado
          </button>
        </form>
      </main>
    </DashboardShell>
  );
}
