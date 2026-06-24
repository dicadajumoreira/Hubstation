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

        <p className="text-xs text-g60 -mt-4">
          Organizado na <strong>sequência da revista</strong>. Seções
          pesquisadas e as preenchidas por cada condomínio aparecem como nota
          (sem campo aqui).
        </p>

        {/* 1 · S01 Capa — Foto de capa */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            1 · Foto de capa
          </h2>
          <Field
            label="Foto de capa"
            hint="JPG, PNG ou WebP. Máx 8MB. Aparece como fundo da capa da revista (S01)."
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

        {/* 2 · S02 Carta do Síndico — tema */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            2 · Carta do Síndico — tema
          </h2>
          {sugSindico && (
            <div className="rounded-lg bg-mint-50 border border-mint-100 px-4 py-3 text-sm">
              <div className="text-xs font-semibold uppercase tracking-wider text-mint-700 mb-1">
                Sugestão para {MESES[mes - 1]}
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
        </section>

        {/* 3 · S03 Agenda Cultural — pesquisada */}
        <InfoSection
          n="3"
          title="Agenda Cultural"
          note="Pesquisada automaticamente em jornais, revistas, portais, plataformas de streaming, teatros e cinemas. Sem campo a preencher."
        />

        {/* 4 · S02B Carta do Gestor — tema (condicional: só com gestor) */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            4 · Carta do Gestor — tema
          </h2>
          <p className="text-xs text-g60 -mt-3">
            Só entra na revista dos condomínios que têm gestor.
          </p>
          {sugGestor && (
            <div className="rounded-lg border border-onix-100 px-4 py-3 text-sm" style={{ background: "#F7EFE9" }}>
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

        {/* 5 · S04 Matéria de Capa */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            5 · Matéria da capa
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
        </section>

        {/* 6 · S05 Dicas Práticas — temas (NOVO) */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            6 · Dicas Práticas — temas
          </h2>
          <Field
            label="Temas das dicas práticas"
            hint="Um tema por linha. A IA gera as dicas do mês a partir desses temas."
          >
            <textarea
              name="dicas_praticas_temas" rows={4}
              defaultValue={ed?.dicas_praticas_temas ?? ""}
              placeholder={"Ex.:\nEconomia de água nas áreas comuns\nSegurança na portaria\nUso consciente do salão de festas"}
              className={inputCls}
            />
          </Field>
        </section>

        {/* 7 · S08 Manutenções — por condomínio */}
        <InfoSection
          n="7"
          title="Manutenções"
          note="Conteúdo por condomínio — cada síndico sobe os itens no formulário da revista do próprio condomínio."
        />

        {/* 8 · S09 Eventos — por condomínio, condicional */}
        <InfoSection
          n="8"
          title="Eventos"
          note="Condicional: só entra se o condomínio marcar que teve eventos no mês. Aparece logo após as Manutenções. Conteúdo por condomínio."
        />

        {/* 9 · S10 Receita do mês */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            9 · Receita do mês
          </h2>
          {sugReceita && (
            <div className="rounded-lg border border-onix-100 px-4 py-3 text-sm" style={{ background: "#F7EFE9" }}>
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

        {/* 10 · S12B Vida Condominial — tema (NOVO) */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            10 · Vida Condominial — tema
          </h2>
          <Field
            label="Tema da matéria de vida condominial"
            hint="A IA escreve a matéria de lifestyle do mês a partir deste tema."
          >
            <input
              type="text" name="vida_condominial_tema"
              defaultValue={ed?.vida_condominial_tema ?? ""}
              placeholder="Ex.: Convivência saudável entre vizinhos"
              className={inputCls}
            />
          </Field>
        </section>

        {/* 11 · S13 Signos do mês — pesquisado */}
        <InfoSection
          n="11"
          title="Signos do mês"
          note="Pesquisado em portais, revistas e jornais especializados de astrologia. Sem campo a preencher."
        />

        {/* Notas pro editor (opcional) */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Notas pro editor (opcional)
          </h2>
          <Field label="Notas que valem pro mês inteiro">
            <textarea
              name="notas_editor_geral" rows={3}
              defaultValue={ed?.notas_editor_geral ?? ""}
              placeholder="Avisos, datas-chave que afetam todas as revistas."
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

function InfoSection({
  n,
  title,
  note,
}: {
  n: string;
  title: string;
  note: string;
}) {
  return (
    <section className="rounded-xl border border-dashed border-onix-200 bg-onix-50/40 p-6">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-onix-500">
        {n} · {title}
      </h2>
      <p className="text-sm text-g60 mt-2">{note}</p>
    </section>
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
