import { cookies } from "next/headers";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { condoFromSlug, slugifyCondo } from "@/lib/sindicompany/condominios";
import {
  getCondoMeta,
  getCondoFotoPublicUrl,
  listCondoMetas,
  type CondoMeta,
} from "@/lib/sindicompany/condominios-db";
import {
  copiarEquipeParaTodosAction,
  renomearCondominioAction,
  salvarCondoMetaAction,
} from "./actions";

/** Resolve o nome do condominio a partir do slug: tenta a lista
 *  canonica estatica; se nao achar, procura nos condominios criados
 *  via banco (condominios_meta). */
async function resolveCondoNome(slug: string): Promise<string | null> {
  const estatico = condoFromSlug(slug);
  if (estatico) return estatico;
  try {
    const metas = await listCondoMetas();
    const m = metas.find((x) => slugifyCondo(x.nome) === slug);
    return m?.nome ?? null;
  } catch {
    return null;
  }
}

function getStr(s: Record<string, string | string[] | undefined>, k: string): string {
  const v = s[k];
  return Array.isArray(v) ? v[0] ?? "" : v ?? "";
}

async function safeGetMeta(nome: string): Promise<{ meta: CondoMeta | null; error: string | null }> {
  try {
    return { meta: await getCondoMeta(nome), error: null };
  } catch (e) {
    return { meta: null, error: e instanceof Error ? e.message : String(e) };
  }
}

export default async function EditarCondoPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  const { slug } = await params;
  const nome = await resolveCondoNome(slug);
  if (!nome) notFound();

  const sp = await searchParams;
  const error = getStr(sp, "error");
  const renamed = getStr(sp, "renamed") === "1";
  const equipeCopiada = getStr(sp, "equipe_copiada");

  const { meta, error: dbError } = await safeGetMeta(nome);

  const sindicoFotoUrl = meta?.sindico_foto_path
    ? getCondoFotoPublicUrl(meta.sindico_foto_path)
    : null;
  const gestorFotoUrl = meta?.gestor_foto_path
    ? getCondoFotoPublicUrl(meta.gestor_foto_path)
    : null;
  const comunidadeQrUrl = meta?.comunidade_qrcode_path
    ? getCondoFotoPublicUrl(meta.comunidade_qrcode_path)
    : null;

  return (
    <main className="max-w-3xl mx-auto px-6 py-12">
      <Link
        href="/sindicompany/condominios"
        className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
      >
        ← Voltar para condomínios
      </Link>

      <header className="mb-10 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
            Condomínio
          </div>
          <h1 className="text-3xl font-bold text-onix-900">{nome}</h1>
          <p className="text-sm text-g60 mt-2 max-w-xl">
            Cadastre síndico(a), gestor, equipe de atendimento, logos, contatos
            e comunidade. Tudo fica salvo e é reaproveitado nas revistas.
          </p>
        </div>
        <Link
          href={`/sindicompany/condominios/${slugifyCondo(nome)}/boas-vindas`}
          className="inline-flex items-center px-4 py-2.5 rounded-lg border border-onix-200 text-onix-900 font-medium hover:bg-onix-50 text-sm whitespace-nowrap"
        >
          📰 Revista de Boas-Vindas
        </Link>
      </header>

      {(error || dbError) && (
        <div className="mb-5 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-900">
          {error || dbError}
        </div>
      )}
      {renamed && (
        <div className="mb-5 rounded-lg bg-mint-50 border border-mint-100 px-4 py-3 text-sm text-mint-700">
          Condomínio renomeado com sucesso.
        </div>
      )}
      {equipeCopiada && (
        <div className="mb-5 rounded-lg bg-mint-50 border border-mint-100 px-4 py-3 text-sm text-mint-700">
          {equipeCopiada}
        </div>
      )}

      <form action={salvarCondoMetaAction} encType="multipart/form-data" className="space-y-8">
        <input type="hidden" name="slug" value={slugifyCondo(nome)} />
        <input type="hidden" name="condo_nome" value={nome} />
        <input type="hidden" name="sindico_foto_existente" value={meta?.sindico_foto_path ?? ""} />

        {/* ============ SÍNDICO ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Síndico(a)
          </h2>

          <Field
            label="By Sindicompany"
            hint="Se marcado, a revista deste condomínio usa o logotipo do By Sindicompany (Assets BySindicompany) no lugar do logo Sindicompany — LOGO 2 em página de fundo branco, LOGO 1 em fundo escuro."
          >
            <label className="flex items-center gap-2 text-sm mt-1">
              <input
                type="checkbox"
                name="is_by_sindico"
                value="on"
                defaultChecked={!!meta?.is_by_sindico}
              />
              Este síndico faz parte do By Sindicompany
            </label>
          </Field>

          <Field label="Nome">
            <input
              type="text"
              name="sindico_nome"
              required
              defaultValue={meta?.sindico_nome ?? ""}
              placeholder="Ex: Juliana Moreira"
              className={inputCls}
            />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="E-mail">
              <input
                type="email"
                name="sindico_email"
                defaultValue={meta?.sindico_email ?? ""}
                placeholder="sindico@email.com"
                className={inputCls}
              />
            </Field>
            <Field label="WhatsApp">
              <input
                type="text"
                name="sindico_whatsapp"
                defaultValue={meta?.sindico_whatsapp ?? ""}
                placeholder="(11) 99999-9999"
                className={inputCls}
              />
            </Field>
          </div>

          <Field
            label="Tipo / gênero"
            hint="Quando for 'Empresa' (sindicatura profissional), a revista fala com os moradores como uma equipe (nós), não como pessoa. Nesse caso, o 'Nome' acima é o nome da empresa."
          >
            <div className="flex gap-4 mt-1 flex-wrap">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="sindico_genero"
                  value="feminino"
                  required
                  defaultChecked={meta?.sindico_genero === "feminino"}
                />
                Síndica
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="sindico_genero"
                  value="masculino"
                  defaultChecked={meta?.sindico_genero === "masculino"}
                />
                Síndico
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="sindico_genero"
                  value="empresa"
                  defaultChecked={meta?.sindico_genero === "empresa"}
                />
                Empresa / Sindicatura profissional
              </label>
            </div>
          </Field>

          <Field
            label="Foto / logo"
            hint="JPG, PNG ou WebP. Máx 5MB. Aparece na seção 'Carta do Síndico' da revista. Para empresa, pode usar o logo dela."
          >
            {sindicoFotoUrl && (
              <div className="mb-3 flex items-center gap-3">
                <Image
                  src={sindicoFotoUrl}
                  alt={`Foto de ${meta?.sindico_nome ?? "síndico"}`}
                  width={80}
                  height={80}
                  unoptimized
                  className="rounded-full object-cover w-20 h-20 border border-onix-100"
                />
                <span className="text-xs text-g60">
                  Foto atual. Suba uma nova abaixo para substituir.
                </span>
              </div>
            )}
            <input
              type="file"
              name="sindico_foto"
              accept="image/jpeg,image/png,image/webp"
              className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100"
            />
          </Field>
        </section>

        {/* ============ SEGUNDO SÍNDICO (DUPLA) ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Segundo síndico(a) — opcional (dupla de síndicos)
          </h2>
          <p className="text-xs text-g60 -mt-3">
            Quando preenchido, a revista de Boas-Vindas e a Mensal escrevem em <strong>plural</strong> (&quot;Caros moradores, agradecemos pela confiança em nossa eleição como síndicos…&quot;), com concordância automática conforme o gênero da dupla.
          </p>
          <input type="hidden" name="sindico2_foto_existente" value={meta?.sindico2_foto_path ?? ""} />

          <Field label="Nome">
            <input
              type="text"
              name="sindico2_nome"
              defaultValue={meta?.sindico2_nome ?? ""}
              placeholder="Deixe em branco se não houver"
              className={inputCls}
            />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="E-mail">
              <input type="email" name="sindico2_email" defaultValue={meta?.sindico2_email ?? ""} className={inputCls} />
            </Field>
            <Field label="WhatsApp">
              <input type="text" name="sindico2_whatsapp" defaultValue={meta?.sindico2_whatsapp ?? ""} className={inputCls} />
            </Field>
          </div>

          <Field label="Tipo / gênero">
            <div className="flex gap-4 mt-1 flex-wrap">
              <label className="flex items-center gap-2 text-sm">
                <input type="radio" name="sindico2_genero" value="feminino" defaultChecked={meta?.sindico2_genero === "feminino"} />
                Síndica
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="radio" name="sindico2_genero" value="masculino" defaultChecked={meta?.sindico2_genero === "masculino"} />
                Síndico
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="radio" name="sindico2_genero" value="empresa" defaultChecked={meta?.sindico2_genero === "empresa"} />
                Empresa
              </label>
            </div>
          </Field>

          <Field label="Foto / logo" hint="JPG/PNG/WebP, até 5MB.">
            {meta?.sindico2_foto_path && (
              <div className="mb-3 flex items-center gap-3">
                <Image
                  src={getCondoFotoPublicUrl(meta.sindico2_foto_path)}
                  alt={`Foto de ${meta.sindico2_nome ?? "segundo síndico"}`}
                  width={80}
                  height={80}
                  unoptimized
                  className="rounded-full object-cover w-20 h-20 border border-onix-100"
                />
                <span className="text-xs text-g60">Foto atual. Suba uma nova abaixo para substituir.</span>
              </div>
            )}
            <input
              type="file"
              name="sindico2_foto"
              accept="image/jpeg,image/png,image/webp"
              className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100"
            />
          </Field>
        </section>

        {/* ============ GESTOR DE ATENDIMENTO ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Gestor de Atendimento
          </h2>
          <p className="text-xs text-g60 -mt-3">
            Pessoa de contato da Sindicompany pra esse condomínio. Aparece na
            carta do gestor da revista.
          </p>

          <Field label="Este condomínio tem Gestor de Atendimento?">
            <div className="flex gap-4 mt-1">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="tem_gestor"
                  value="sim"
                  defaultChecked={!!meta?.gestor_nome}
                />
                Sim, tem gestor
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="tem_gestor"
                  value="nao"
                  defaultChecked={!meta?.gestor_nome}
                />
                Não tem gestor
              </label>
            </div>
          </Field>

          <Field label="Nome" hint="Nome de quem atende esse condomínio (só se tiver gestor).">
            <input
              type="hidden"
              name="gestor_foto_existente"
              value={meta?.gestor_foto_path ?? ""}
            />
            <input
              type="text"
              name="gestor_nome"
              defaultValue={meta?.gestor_nome ?? ""}
              maxLength={120}
              placeholder="Ex: Carlos Andrade"
              className={inputCls}
            />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="E-mail">
              <input
                type="email"
                name="gestor_email"
                defaultValue={meta?.gestor_email ?? ""}
                placeholder="gestor@email.com"
                className={inputCls}
              />
            </Field>
            <Field label="WhatsApp">
              <input
                type="text"
                name="gestor_whatsapp"
                defaultValue={meta?.gestor_whatsapp ?? ""}
                placeholder="(11) 99999-9999"
                className={inputCls}
              />
            </Field>
          </div>

          <Field label="Gênero" hint="Define o título: Gestor / Gestora de Atendimento.">
            <div className="flex gap-4 mt-1">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="gestor_genero"
                  value="feminino"
                  defaultChecked={meta?.gestor_genero === "feminino"}
                />
                Gestora de Atendimento
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="gestor_genero"
                  value="masculino"
                  defaultChecked={
                    meta?.gestor_genero === "masculino" || !meta?.gestor_genero
                  }
                />
                Gestor de Atendimento
              </label>
            </div>
          </Field>

          <Field
            label="Foto"
            hint="JPG, PNG ou WebP. Máx 5MB. Opcional."
          >
            {gestorFotoUrl && (
              <div className="mb-3 flex items-center gap-3">
                <Image
                  src={gestorFotoUrl}
                  alt={`Foto de ${meta?.gestor_nome ?? "gestor"}`}
                  width={80}
                  height={80}
                  unoptimized
                  className="rounded-full object-cover w-20 h-20 border border-onix-100"
                />
                <span className="text-xs text-g60">
                  Foto atual. Suba uma nova abaixo para substituir.
                </span>
              </div>
            )}
            <input
              type="file"
              name="gestor_foto"
              accept="image/jpeg,image/png,image/webp"
              className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100"
            />
          </Field>
        </section>

        {/* ============ SEGUNDO GESTOR (DUPLA) ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Segundo gestor(a) — opcional (dupla de gestores)
          </h2>
          <p className="text-xs text-g60 -mt-3">
            Quando preenchido, a revista refere a dupla no plural: &quot;Gestores de Atendimento&quot; (M+M ou misto), &quot;Gestoras de Atendimento&quot; (F+F).
          </p>
          <input type="hidden" name="gestor2_foto_existente" value={meta?.gestor2_foto_path ?? ""} />

          <Field label="Nome">
            <input
              type="text"
              name="gestor2_nome"
              defaultValue={meta?.gestor2_nome ?? ""}
              placeholder="Deixe em branco se não houver"
              className={inputCls}
            />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="E-mail">
              <input type="email" name="gestor2_email" defaultValue={meta?.gestor2_email ?? ""} className={inputCls} />
            </Field>
            <Field label="WhatsApp">
              <input type="text" name="gestor2_whatsapp" defaultValue={meta?.gestor2_whatsapp ?? ""} className={inputCls} />
            </Field>
          </div>

          <Field label="Gênero">
            <div className="flex gap-4 mt-1 flex-wrap">
              <label className="flex items-center gap-2 text-sm">
                <input type="radio" name="gestor2_genero" value="feminino" defaultChecked={meta?.gestor2_genero === "feminino"} />
                Gestora
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="radio" name="gestor2_genero" value="masculino" defaultChecked={meta?.gestor2_genero === "masculino"} />
                Gestor
              </label>
            </div>
          </Field>

          <Field label="Foto" hint="JPG/PNG/WebP, até 5MB.">
            {meta?.gestor2_foto_path && (
              <div className="mb-3 flex items-center gap-3">
                <Image
                  src={getCondoFotoPublicUrl(meta.gestor2_foto_path)}
                  alt={`Foto de ${meta.gestor2_nome ?? "segundo gestor"}`}
                  width={80}
                  height={80}
                  unoptimized
                  className="rounded-full object-cover w-20 h-20 border border-onix-100"
                />
                <span className="text-xs text-g60">Foto atual. Suba uma nova abaixo para substituir.</span>
              </div>
            )}
            <input
              type="file"
              name="gestor2_foto"
              accept="image/jpeg,image/png,image/webp"
              className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100"
            />
          </Field>
        </section>

        {/* ============ LOGOTIPO DO SÍNDICO ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Logotipo do síndico
          </h2>
          <p className="text-xs text-g60 -mt-3">
            Default usado nas revistas (capa e contracapa). Substitui o logo
            Sindicompany quando preenchido.
          </p>

          <Field
            label="Logo"
            hint="JPG, PNG ou WebP transparente. Máx 5MB."
          >
            <input
              type="hidden"
              name="logo_sindico_existente"
              value={meta?.logo_url ?? ""}
            />
            {meta?.logo_url && (
              <div className="mb-3 flex items-start gap-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={meta.logo_url}
                  alt={`Logo do síndico de ${nome}`}
                  className="rounded-lg object-contain bg-onix-50 w-32 h-20 border border-onix-100 p-2"
                />
                <span className="text-xs text-g60 mt-1">
                  Logo atual. Suba um novo abaixo para substituir.
                </span>
              </div>
            )}
            <input
              type="file"
              name="logo_sindico_file"
              accept="image/jpeg,image/png,image/webp"
              className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100"
            />
          </Field>
        </section>

        {/* ============ LOGOTIPO DO CONDOMÍNIO ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Logotipo do condomínio
          </h2>
          <p className="text-xs text-g60 -mt-3">
            Logo oficial do condomínio (placa, fachada, identidade visual).
            Não substitui o do síndico na revista — fica disponível pra usos
            específicos (peças avulsas, comunicados, etc).
          </p>

          <Field
            label="Logo"
            hint="JPG, PNG ou WebP transparente. Máx 5MB."
          >
            <input
              type="hidden"
              name="logo_condominio_existente"
              value={meta?.logo_condominio_url ?? ""}
            />
            {meta?.logo_condominio_url && (
              <div className="mb-3 flex items-start gap-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={meta.logo_condominio_url}
                  alt={`Logo do condomínio ${nome}`}
                  className="rounded-lg object-contain bg-onix-50 w-32 h-20 border border-onix-100 p-2"
                />
                <span className="text-xs text-g60 mt-1">
                  Logo atual. Suba um novo abaixo para substituir.
                </span>
              </div>
            )}
            <input
              type="file"
              name="logo_condominio_file"
              accept="image/jpeg,image/png,image/webp"
              className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100"
            />
          </Field>
        </section>

        {/* ============ COMUNIDADE DO CONDOMÍNIO ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Comunidade do condomínio
          </h2>
          <p className="text-xs text-g60 -mt-3">
            Link da comunidade (grupo, app, canal) e o QR code que leva pra
            ela. Aparecem na revista. Ambos opcionais.
          </p>

          <Field label="Link da comunidade">
            <input
              type="text"
              name="comunidade_url"
              defaultValue={meta?.comunidade_url ?? ""}
              maxLength={500}
              placeholder="https://chat.whatsapp.com/... ou link do app"
              className={inputCls}
            />
          </Field>

          <Field
            label="QR code da comunidade"
            hint="JPG, PNG ou WebP. Máx 5MB. Suba a imagem do QR code."
          >
            <input
              type="hidden"
              name="comunidade_qr_existente"
              value={meta?.comunidade_qrcode_path ?? ""}
            />
            {comunidadeQrUrl && (
              <div className="mb-3 flex items-center gap-3">
                <Image
                  src={comunidadeQrUrl}
                  alt="QR code da comunidade"
                  width={96}
                  height={96}
                  unoptimized
                  className="rounded object-contain bg-white w-24 h-24 border border-onix-100 p-1"
                />
                <span className="text-xs text-g60">
                  QR atual. Suba um novo abaixo para substituir.
                </span>
              </div>
            )}
            <input
              type="file"
              name="comunidade_qr"
              accept="image/jpeg,image/png,image/webp"
              className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100"
            />
          </Field>
        </section>

        {/* ============ EQUIPE DE ATENDIMENTO ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Equipe de Atendimento
          </h2>
          <p className="text-xs text-g60 -mt-3">
            Até 5 pessoas que atendem o condomínio (foto, nome e cargo).
            Aparecem na Revista de Boas-Vindas. Deixe nome/cargo em branco
            pra slots não usados.
          </p>
          {[0, 1, 2, 3, 4].map((i) => {
            const m = meta?.equipe_atendimento?.[i];
            const fotoUrl = m?.foto_path ? getCondoFotoPublicUrl(m.foto_path) : null;
            return (
              <div
                key={i}
                className="rounded-lg border border-onix-100 p-3 flex items-center gap-3"
              >
                <div className="shrink-0">
                  <input
                    type="hidden"
                    name={`equipe_foto_existente_${i + 1}`}
                    value={m?.foto_path ?? ""}
                  />
                  {fotoUrl ? (
                    <Image
                      src={fotoUrl}
                      alt={`Foto ${i + 1}`}
                      width={56}
                      height={56}
                      unoptimized
                      className="rounded-full object-cover w-14 h-14 border border-onix-100"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-onix-50 border border-onix-100" />
                  )}
                </div>
                <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input
                    type="text"
                    name={`equipe_nome_${i + 1}`}
                    defaultValue={m?.nome ?? ""}
                    maxLength={120}
                    placeholder={`Nome (membro ${i + 1})`}
                    className={inputCls}
                  />
                  <input
                    type="text"
                    name={`equipe_cargo_${i + 1}`}
                    defaultValue={m?.cargo ?? ""}
                    maxLength={120}
                    placeholder="Cargo (ex: Analista de Atendimento)"
                    className={inputCls}
                  />
                </div>
                <div className="shrink-0">
                  <input
                    type="file"
                    name={`equipe_foto_${i + 1}`}
                    accept="image/jpeg,image/png,image/webp"
                    className="block w-40 text-[11px] text-onix-800 file:mr-1 file:rounded file:border file:border-onix-100 file:bg-onix-50 file:px-2 file:py-1 file:text-[11px] file:font-medium hover:file:bg-onix-100"
                  />
                </div>
              </div>
            );
          })}

          <Field
            label="Contato do(a) síndico(a) na revista"
            hint="Escolha o que aparece junto do nome e cargo do(a) síndico(a). O nome e o cargo aparecem sempre."
          >
            <div className="flex flex-col gap-1.5 mt-1">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  name="mostrar_whatsapp_sindico"
                  value="on"
                  defaultChecked={meta ? meta.mostrar_whatsapp_sindico !== false : true}
                />
                Mostrar WhatsApp do(a) síndico(a)
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  name="mostrar_email_sindico"
                  value="on"
                  defaultChecked={meta ? meta.mostrar_email_sindico !== false : true}
                />
                Mostrar e-mail do(a) síndico(a)
              </label>
            </div>
          </Field>
        </section>

        {/* ============ REVISTA DE BOAS-VINDAS ============ */}
        <section className="bg-white rounded-xl border border-onix-100 p-6 space-y-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Revista de Boas-Vindas
          </h2>
          <p className="text-xs text-g60 -mt-3">
            Foto de capa da Revista de Boas-Vindas (página 1). Opcional — se
            não tiver, a capa usa um fundo em degradê da marca.
          </p>
          <Field
            label="Foto de capa"
            hint="JPG, PNG ou WebP. Máx 5MB. Vai como fundo da primeira página."
          >
            <input
              type="hidden"
              name="boasvindas_capa_existente"
              value={meta?.boasvindas_capa_path ?? ""}
            />
            {meta?.boasvindas_capa_path && (
              <div className="mb-3 flex items-center gap-3">
                <Image
                  src={getCondoFotoPublicUrl(meta.boasvindas_capa_path)}
                  alt="Capa da Revista de Boas-Vindas"
                  width={120}
                  height={160}
                  unoptimized
                  className="rounded object-cover w-28 h-36 border border-onix-100"
                />
                <span className="text-xs text-g60">
                  Capa atual. Suba uma nova abaixo para substituir.
                </span>
              </div>
            )}
            <input
              type="file"
              name="boasvindas_capa"
              accept="image/jpeg,image/png,image/webp"
              className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100"
            />
          </Field>
        </section>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            className="rounded-lg bg-onix-900 text-white px-5 py-2.5 font-medium hover:bg-onix-800"
          >
            Salvar
          </button>
          <Link
            href="/sindicompany/condominios"
            className="rounded-lg border border-onix-100 px-5 py-2.5 font-medium hover:bg-onix-50"
          >
            Cancelar
          </Link>
        </div>
      </form>

      {/* Copiar a equipe deste condominio para TODOS os outros condominios
          cadastrados (e criar cadastro minimo pros da lista estatica que
          ainda nao tem). Util quando a equipe operacional e a mesma. */}
      {meta?.equipe_atendimento && meta.equipe_atendimento.length > 0 && (
        <section className="mt-10 rounded-xl border border-onix-100 bg-white p-6">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700 mb-2">
            Equipe de atendimento — replicar para todos
          </h2>
          <p className="text-sm text-g60 mb-4">
            Copia a equipe de atendimento deste condomínio para <strong>todos os outros</strong>{" "}
            condomínios. Para os que ainda não têm cadastro, cria um cadastro mínimo com a
            equipe. Outros campos dos demais condomínios não são alterados.
          </p>
          <form action={copiarEquipeParaTodosAction}>
            <input type="hidden" name="slug" value={slugifyCondo(nome)} />
            <input type="hidden" name="condo_nome" value={nome} />
            <button
              type="submit"
              className="inline-flex items-center px-4 py-2 rounded-lg bg-mint-600 text-white text-sm font-medium hover:bg-mint-700"
            >
              Replicar esta equipe para todos os condomínios
            </button>
          </form>
        </section>
      )}

      {/* Renomear condominio (acao separada). Atualiza meta + referencias em
          revistas e comunicados. Itens da lista estatica que tenham o mesmo
          nome continuam aparecendo na lista, sem cadastro. */}
      <section className="mt-10 rounded-xl border border-onix-100 bg-white p-6">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-mint-700 mb-2">
          Renomear condomínio
        </h2>
        <p className="text-sm text-g60 mb-4">
          Use este campo para corrigir o nome do condomínio. A alteração é
          aplicada no cadastro e em todas as revistas e comunicados que
          referenciam este nome.
        </p>
        <form action={renomearCondominioAction} className="flex flex-wrap items-end gap-3">
          <input type="hidden" name="slug" value={slugifyCondo(nome)} />
          <input type="hidden" name="condo_nome_atual" value={nome} />
          <div className="flex-1 min-w-[240px]">
            <label className="block text-xs font-medium text-onix-900 mb-1">Novo nome</label>
            <input
              name="condo_nome_novo"
              defaultValue={nome}
              required
              maxLength={140}
              className="w-full rounded-lg border border-onix-200 px-3 py-2 text-sm"
            />
          </div>
          <button
            type="submit"
            className="inline-flex items-center px-4 py-2 rounded-lg bg-onix-900 text-white text-sm font-medium hover:bg-onix-800"
          >
            Renomear
          </button>
        </form>
      </section>
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
