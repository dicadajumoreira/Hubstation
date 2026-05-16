import { cookies } from "next/headers";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { CONDOMINIOS } from "@/lib/sindicompany/condominios";
import {
  getComunicado,
  getComunicadoIlustracaoUrl,
} from "@/lib/sindicompany/comunicados";
import {
  getCondoMeta,
  listByLogoUrls,
  listCondoMetas,
} from "@/lib/sindicompany/condominios-db";
import { DashboardShell } from "../../shell";
import { ComunicadoArt } from "../comunicado-art";
import { DownloadButtons } from "./download-buttons";
import {
  excluirComunicadoAction,
  gerarTextoComIaAction,
  removerIlustracaoAction,
  salvarComunicadoAction,
  uploadIlustracaoAction,
} from "./actions";

export default async function ComunicadoPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ error?: string; saved?: string; gerado?: string; ilustracao?: string }>;
}) {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) redirect("/sindicompany/login");

  const { id } = await params;
  const sp = await searchParams;
  const c = await getComunicado(id).catch(() => null);
  if (!c) notFound();

  const meta = await getCondoMeta(c.condominio).catch(() => null);
  const ehBy = meta?.is_by_sindico === true;
  const byLogos = ehBy ? await listByLogoUrls().catch(() => [] as (string | null)[]) : [];
  // Comunicado tem fundo claro -> LOGO 2 do By; cai pro slot 1.
  const byLogoUrl = ehBy ? (byLogos[1] ?? byLogos[0] ?? null) : null;
  const ilustracaoUrl = c.ilustracao_path ? getComunicadoIlustracaoUrl(c.ilustracao_path) : null;

  let nomes: string[] = [...CONDOMINIOS];
  try {
    const ms = await listCondoMetas();
    nomes = Array.from(new Set<string>([...CONDOMINIOS, ...ms.map((m) => m.nome)]));
  } catch { /* mantem lista estatica */ }
  nomes.sort((a, b) => a.localeCompare(b, "pt-BR", { sensitivity: "base" }));

  const baseName = `comunicado-${c.condominio}-${c.titulo}`.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

  const artProps = {
    condominio: c.condominio,
    titulo: c.titulo,
    subtitulo: c.subtitulo,
    corpo: c.corpo,
    ilustracaoUrl,
    logoCondominioUrl: meta?.logo_condominio_url ?? null,
    logoSindicoUrl: meta?.logo_url ?? null,
    byLogoUrl,
    ehBy,
  };

  const A4_SCALE = 0.46;
  const CEL_SCALE = 0.27;

  return (
    <DashboardShell>
      <main className="max-w-5xl mx-auto px-6 py-12">
        <Link href="/sindicompany/comunicados" className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block">
          ← Voltar para comunicados
        </Link>

        <header className="mb-8 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">{c.condominio}</div>
            <h1 className="text-2xl font-bold text-onix-900">{c.titulo}{c.subtitulo && <span className="text-g60 font-normal"> · {c.subtitulo}</span>}</h1>
          </div>
          <DownloadButtons baseName={baseName} />
        </header>

        {sp.error && <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{sp.error}</div>}
        {sp.saved && <div className="mb-6 rounded-lg border border-mint-100 bg-mint-50 px-4 py-3 text-sm text-mint-700">Comunicado salvo.</div>}
        {sp.gerado && <div className="mb-6 rounded-lg border border-mint-100 bg-mint-50 px-4 py-3 text-sm text-mint-700">Texto gerado com IA. Revise abaixo se quiser ajustar.</div>}
        {sp.ilustracao && <div className="mb-6 rounded-lg border border-mint-100 bg-mint-50 px-4 py-3 text-sm text-mint-700">Ilustração atualizada.</div>}

        {/* Previews */}
        <div className="flex flex-wrap gap-8 mb-12">
          <div>
            <div className="text-xs uppercase tracking-wider text-g60 font-semibold mb-2">Formato A4</div>
            <div style={{ width: 794 * A4_SCALE, height: 1123 * A4_SCALE, overflow: "hidden", borderRadius: 8, boxShadow: "0 2px 14px rgba(0,0,0,.14)", background: "#FBFAF6" }}>
              <div style={{ transform: `scale(${A4_SCALE})`, transformOrigin: "top left", width: 794, height: 1123 }}>
                <ComunicadoArt nodeId="comunicado-a4" variant="a4" {...artProps} />
              </div>
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-g60 font-semibold mb-2">Formato Celular (Story 9:16)</div>
            <div style={{ width: 1080 * CEL_SCALE, height: 1920 * CEL_SCALE, overflow: "hidden", borderRadius: 8, boxShadow: "0 2px 14px rgba(0,0,0,.14)", background: "#FBFAF6" }}>
              <div style={{ transform: `scale(${CEL_SCALE})`, transformOrigin: "top left", width: 1080, height: 1920 }}>
                <ComunicadoArt nodeId="comunicado-celular" variant="celular" {...artProps} />
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-10 lg:grid-cols-2">
          {/* Editar conteudo */}
          <section>
            <h2 className="text-lg font-semibold text-onix-900 mb-4">Editar comunicado</h2>
            <form action={salvarComunicadoAction} className="space-y-4">
              <input type="hidden" name="id" value={c.id} />
              <div>
                <label className="block text-sm font-medium text-onix-900 mb-1">Condomínio</label>
                <select name="condominio" defaultValue={c.condominio} className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm">
                  {!nomes.includes(c.condominio) && <option value={c.condominio}>{c.condominio}</option>}
                  {nomes.map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-onix-900 mb-1">Título</label>
                <input name="titulo" defaultValue={c.titulo} maxLength={90} required className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-onix-900 mb-1">Subtítulo <span className="text-g60 font-normal">(opcional)</span></label>
                <input name="subtitulo" defaultValue={c.subtitulo ?? ""} maxLength={90} className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-onix-900 mb-1">Briefing <span className="text-g60 font-normal">(referência / usado pela IA)</span></label>
                <textarea name="briefing" defaultValue={c.briefing ?? ""} rows={3} className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-onix-900 mb-1">Texto do comunicado</label>
                <textarea name="corpo" defaultValue={c.corpo} rows={12} className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm font-mono" />
                <p className="text-[11px] text-g60 mt-1">Cerca de 150–190 palavras / 4-5 parágrafos curtos cabem bem no Story (1080×1920) e no A4. Acima disso pode cortar na arte.</p>
              </div>
              <button type="submit" className="inline-flex items-center px-5 py-2.5 rounded-lg bg-onix-900 text-white font-medium hover:bg-onix-800 text-sm">Salvar</button>
            </form>
          </section>

          {/* IA + ilustracao + excluir */}
          <section className="space-y-8">
            <div className="rounded-xl border border-onix-100 bg-white p-5">
              <h2 className="text-lg font-semibold text-onix-900 mb-1">Gerar texto com IA</h2>
              <p className="text-sm text-g60 mb-4">Descreva em poucas linhas o que precisa ser comunicado. A IA escreve o comunicado formal e substitui o texto atual.</p>
              <form action={gerarTextoComIaAction} className="space-y-3">
                <input type="hidden" name="id" value={c.id} />
                <textarea name="briefing" defaultValue={c.briefing ?? ""} rows={4} required placeholder="Ex.: reforçar que não é permitido deixar lixo no chão; só dentro das lixeiras…" className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm" />
                <button type="submit" className="inline-flex items-center px-4 py-2 rounded-lg bg-mint-600 text-white text-sm font-medium hover:bg-mint-700">Gerar texto</button>
              </form>
            </div>

            <div className="rounded-xl border border-onix-100 bg-white p-5">
              <h2 className="text-lg font-semibold text-onix-900 mb-1">Ilustração (canto superior direito)</h2>
              <p className="text-sm text-g60 mb-4">PNG/JPG/WebP/SVG, até 6MB. Ideal: imagem com fundo transparente (PNG).</p>
              {ilustracaoUrl && (
                <div className="mb-4 flex items-center gap-4">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={ilustracaoUrl} alt="Ilustração atual" className="h-20 w-auto object-contain border border-onix-100 rounded bg-white" />
                  <form action={removerIlustracaoAction}>
                    <input type="hidden" name="id" value={c.id} />
                    <button type="submit" className="text-xs text-rose-600 hover:underline">Remover</button>
                  </form>
                </div>
              )}
              <form action={uploadIlustracaoAction} className="space-y-3">
                <input type="hidden" name="id" value={c.id} />
                <input type="file" name="ilustracao" accept="image/png,image/jpeg,image/webp,image/svg+xml" required className="block text-sm" />
                <button type="submit" className="inline-flex items-center px-4 py-2 rounded-lg bg-onix-900 text-white text-sm font-medium hover:bg-onix-800">Enviar ilustração</button>
              </form>
            </div>

            <div className="rounded-xl border border-rose-100 bg-rose-50 p-5">
              <h2 className="text-sm font-semibold text-rose-800 mb-2">Excluir comunicado</h2>
              <form action={excluirComunicadoAction}>
                <input type="hidden" name="id" value={c.id} />
                <button type="submit" className="text-sm text-rose-700 hover:underline">Excluir definitivamente</button>
              </form>
            </div>
          </section>
        </div>
      </main>
    </DashboardShell>
  );
}
