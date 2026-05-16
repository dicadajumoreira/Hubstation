import { cookies } from "next/headers";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  getEditorial,
  parseMesAno,
  formatMesAno,
  type Editorial,
} from "@/lib/sindicompany/editoriais";
import {
  sugerirMateria,
  sugerirReceita,
  sugerirCartaSindico,
  sugerirCartaGestor,
} from "@/lib/sindicompany/sugestoes";
import { salvarEditorialAction } from "./actions";

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

function getStr(s: Record<string, string | string[] | undefined>, k: string): string {
  const v = s[k];
  return Array.isArray(v) ? v[0] ?? "" : v ?? "";
}

async function safeGet(mes: number, ano: number): Promise<{ ed: Editorial | null; error: string | null }> {
  try {
    return { ed: await getEditorial(mes, ano), error: null };
  } catch (e) {
    return { ed: null, error: e instanceof Error ? e.message : String(e) };
  }
}

export default async function EditarEditorialPage({
  params,
  searchParams,
}: {
  params: Promise<{ mesano: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  const { mesano } = await params;
  const parsed = parseMesAno(mesano);
  if (!parsed) notFound();
  const { mes, ano } = parsed;

  const sp = await searchParams;
  const error = getStr(sp, "error");

  const { ed, error: dbError } = await safeGet(mes, ano);

  const sugMateria = sugerirMateria(mes);
  const sugReceita = sugerirReceita(mes);
  const sugSindico = sugerirCartaSindico(mes);
  const sugGestor = sugerirCartaGestor(mes);

  return (
    <main className="max-w-3xl mx-auto px-6 py-12">
      <Link
        href="/sindicompany/editorial"
        className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
      >
        ← Voltar para editorial mensal
      </Link>

      <header className="mb-10">
        <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
          Editorial mensal
        </div>
        <h1 className="text-3xl font-bold text-onix-900">
          {MESES[mes - 1]} <span className="text-g60 tabular-nums">/ {ano}</span>
        </h1>
        <p className="text-sm text-g60 mt-2 max-w-xl">
          Estas decisões valem pra todas as revistas dessa edição. Cada
          condomínio só preenche o conteúdo dele depois.
        </p>
      </header>

      {(error || dbError) && (
        <div className="mb-5 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-900">
          {error || dbError}
        </div>
      )}

      <form action={salvarEditorialAction} encType="multipart/form-data" className="space-y-8">
        <input type="hidden" name="slug" value={formatMesAno(mes, ano)} />

        {/* ============ MATÉRIA DE CAPA ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            1 · Matéria de capa
          </h2>

          {sugMateria && (
            <div className="rounded-lg bg-mint-50 border border-mint-100 px-4 py-3 text-sm">
              <div className="text-xs font-semibold uppercase tracking-wider text-mint-700 mb-1">
                Sugestão para {MESES[mes - 1]}
              </div>
              <div className="font-medium text-onix-900">{sugMateria.titulo}</div>
              <div className="text-onix-800 opacity-80 mt-0.5">{sugMateria.subtitulo}</div>
            </div>
          )}

          <Field label="Título">
            <input
              type="text" name="materia_capa_titulo"
              defaultValue={ed?.materia_capa_titulo ?? sugMateria?.titulo ?? ""}
              className={inputCls}
            />
          </Field>

          <Field label="Subtítulo">
            <textarea
              name="materia_capa_subtitulo" rows={2}
              defaultValue={ed?.materia_capa_subtitulo ?? sugMateria?.subtitulo ?? ""}
              className={inputCls}
            />
          </Field>

          <Field
            label="Foto de capa"
            hint="JPG, PNG ou WebP. Máx 8MB. Aparece como fundo da capa da revista."
          >
            <input type="hidden" name="foto_capa_existente" value={ed?.foto_capa_url ?? ""} />
            {ed?.foto_capa_url && (
              <div className="mb-3 flex items-start gap-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={ed.foto_capa_url}
                  alt="Foto de capa atual"
                  className="rounded-lg object-cover w-32 h-20 border border-onix-100"
                />
                <span className="text-xs text-g60 mt-1">
                  Foto atual. Suba uma nova abaixo para substituir.
                </span>
              </div>
            )}
            <input
              type="file"
              name="foto_capa_file"
              accept="image/jpeg,image/png,image/webp"
              className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100"
            />
          </Field>
        </section>

        {/* ============ RECEITA ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            2 · Receita do mês
          </h2>

          {sugReceita && (
            <div className="rounded-lg bg-sand-50 border border-onix-100 px-4 py-3 text-sm" style={{background:"#F7EFE9"}}>
              <div className="text-xs font-semibold uppercase tracking-wider text-mint-700 mb-1">
                Sugestão para {MESES[mes - 1]}
              </div>
              <div className="font-medium text-onix-900">{sugReceita.titulo}</div>
              <div className="text-onix-800 opacity-80 mt-0.5">{sugReceita.descricao}</div>
            </div>
          )}

          <Field label="Receita">
            <input
              type="text" name="receita_titulo"
              defaultValue={ed?.receita_titulo ?? sugReceita?.titulo ?? ""}
              className={inputCls}
            />
          </Field>

          <Field label="Descrição (opcional)">
            <textarea
              name="receita_descricao" rows={2}
              defaultValue={ed?.receita_descricao ?? sugReceita?.descricao ?? ""}
              className={inputCls}
            />
          </Field>
        </section>

        {/* ============ TEMAS DAS CARTAS ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            3 · Temas sugeridos das cartas
          </h2>
          <p className="text-xs text-g60 -mt-3">
            Os síndicos e gestores escrevem suas próprias cartas, mas os temas
            saem daqui. Pode mudar para qualquer um se a pauta do mês pedir.
          </p>

          {sugSindico && (
            <div className="rounded-lg bg-mint-50 border border-mint-100 px-4 py-3 text-sm">
              <div className="text-xs font-semibold uppercase tracking-wider text-mint-700 mb-1">
                Sugestão para a carta do(a) síndico(a)
              </div>
              <div className="font-medium text-onix-900">{sugSindico.tema}</div>
              <div className="text-onix-800 opacity-80 mt-0.5">{sugSindico.resumo}</div>
            </div>
          )}

          <Field label="Tema da carta do(a) síndico(a)">
            <input
              type="text" name="carta_sindico_tema"
              defaultValue={ed?.carta_sindico_tema ?? sugSindico?.tema ?? ""}
              className={inputCls}
            />
          </Field>

          {sugGestor && (
            <div className="rounded-lg bg-sand-50 border border-onix-100 px-4 py-3 text-sm" style={{background:"#F7EFE9"}}>
              <div className="text-xs font-semibold uppercase tracking-wider text-mint-700 mb-1">
                Sugestão para a carta do gestor
              </div>
              <div className="font-medium text-onix-900">{sugGestor.tema}</div>
              <div className="text-onix-800 opacity-80 mt-0.5">{sugGestor.resumo}</div>
            </div>
          )}

          <Field label="Tema da carta do gestor">
            <input
              type="text" name="carta_gestor_tema"
              defaultValue={ed?.carta_gestor_tema ?? sugGestor?.tema ?? ""}
              className={inputCls}
            />
          </Field>
        </section>

        {/* ============ NOTAS ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            4 · Notas pro editor (opcional)
          </h2>
          <Field label="Notas que valem pro mês inteiro">
            <textarea
              name="notas_editor_geral" rows={3}
              defaultValue={ed?.notas_editor_geral ?? ""}
              placeholder="Avisos, datas-chave, eventos do mês que afetam todas as revistas."
              className={inputCls}
            />
          </Field>
        </section>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            className="rounded-lg bg-onix-900 text-white px-5 py-2.5 font-medium hover:bg-onix-800"
          >
            Salvar editorial
          </button>
          <Link
            href="/sindicompany/editorial"
            className="rounded-lg border border-onix-100 px-5 py-2.5 font-medium hover:bg-onix-50"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </main>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-wider text-onix-800 block mb-1">
        {label}
      </span>
      {children}
      {hint && <span className="text-xs text-g60 mt-1 block">{hint}</span>}
    </label>
  );
}

const inputCls =
  "block w-full rounded-lg border border-onix-100 bg-white px-3.5 py-2.5 text-onix-900 outline-none focus:border-mint-600 focus:ring-2 focus:ring-mint-100";
