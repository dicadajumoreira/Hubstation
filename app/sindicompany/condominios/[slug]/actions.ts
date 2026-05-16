"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { condoFromSlug, slugifyCondo } from "@/lib/sindicompany/condominios";
import {
  copiarEquipeParaTodosCondos,
  renameCondoMeta,
  upsertCondoMeta,
  uploadCondoFoto,
  uploadCondoLogo,
  type CondoMetaInput,
} from "@/lib/sindicompany/condominios-db";
import { CONDOMINIOS } from "@/lib/sindicompany/condominios";
import type { Genero } from "@/lib/sindicompany/db";
import { describeError } from "@/lib/sindicompany/errors";

const MAX_PHOTO_BYTES = 5 * 1024 * 1024; // 5MB
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const EXT_BY_TYPE: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};

async function requireAuth() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }
}

function backWithError(slug: string, message: string): never {
  const params = new URLSearchParams({ error: message });
  redirect(`/sindicompany/condominios/${slug}?${params.toString()}`);
}

function getStr(fd: FormData, key: string): string {
  return String(fd.get(key) ?? "").trim();
}

async function maybeUploadFoto(
  fd: FormData,
  field: string,
  slug: string,
  role: string,
): Promise<string | null> {
  const file = fd.get(field);
  if (!(file instanceof File) || file.size === 0) return null;

  if (file.size > MAX_PHOTO_BYTES) {
    backWithError(slug, `Foto do ${role} maior que 5MB.`);
  }
  if (!ALLOWED_TYPES.has(file.type)) {
    backWithError(slug, `Foto do ${role} precisa ser JPG, PNG ou WebP.`);
  }

  const buf = Buffer.from(await file.arrayBuffer());
  const ext = EXT_BY_TYPE[file.type];
  try {
    return await uploadCondoFoto(slug, role, buf, file.type, ext);
  } catch (e) {
    const msg = describeError(e);
    if (/bucket.*not.*found|not.*found.*bucket/i.test(msg)) {
      backWithError(
        slug,
        "Bucket de fotos não existe. Rode a migration 20260509 no Supabase.",
      );
    }
    backWithError(slug, `Falha ao subir foto do ${role}: ${msg}`);
  }
}

async function maybeUploadLogo(
  fd: FormData,
  field: string,
  slug: string,
  kind: "sindico" | "condominio",
): Promise<string | null> {
  const file = fd.get(field);
  if (!(file instanceof File) || file.size === 0) return null;

  const label = kind === "condominio" ? "Logo do condomínio" : "Logo do síndico";
  if (file.size > MAX_PHOTO_BYTES) {
    backWithError(slug, `${label} maior que 5MB.`);
  }
  if (!ALLOWED_TYPES.has(file.type)) {
    backWithError(slug, `${label} precisa ser JPG, PNG ou WebP.`);
  }

  const buf = Buffer.from(await file.arrayBuffer());
  const ext = EXT_BY_TYPE[file.type];
  try {
    return await uploadCondoLogo(slug, buf, file.type, ext, kind);
  } catch (e) {
    const msg = describeError(e);
    backWithError(slug, `Falha ao subir ${label.toLowerCase()}: ${msg}`);
  }
}

function isNextControlError(e: unknown): boolean {
  // redirect() / notFound() do Next throwam um erro com .digest começando com NEXT_
  // Não devemos engolir; precisa rethrow pra Next executar o redirect.
  if (!e || typeof e !== "object") return false;
  const digest = (e as { digest?: unknown }).digest;
  return typeof digest === "string" && digest.startsWith("NEXT_");
}

export async function salvarCondoMetaAction(formData: FormData): Promise<void> {
  const slug = getStr(formData, "slug");
  try {
    await salvarCondoMetaImpl(formData);
  } catch (e) {
    if (isNextControlError(e)) throw e;
    console.error("[condo-meta] action failed:", e);
    backWithError(slug, `Erro inesperado: ${describeError(e)}`);
  }
}

async function salvarCondoMetaImpl(formData: FormData): Promise<void> {
  await requireAuth();

  const slug = getStr(formData, "slug");
  // Prefere o nome enviado pelo form (resolvido na pagina, cobre
  // condominios criados via banco); cai pra lista estatica como
  // fallback.
  const nome = getStr(formData, "condo_nome") || condoFromSlug(slug) || "";
  if (!nome) {
    redirect("/sindicompany/condominios");
  }

  const sindico_nome = getStr(formData, "sindico_nome");
  const generoRaw = getStr(formData, "sindico_genero");
  const sindico_genero: Genero | undefined =
    generoRaw === "masculino" || generoRaw === "feminino" || generoRaw === "empresa"
      ? generoRaw
      : undefined;

  if (!sindico_nome) backWithError(slug, "Informe o nome do(a) síndico(a) ou da empresa.");
  if (!sindico_genero) backWithError(slug, "Selecione o tipo (síndica / síndico / empresa).");

  const sindicoFotoExistente = getStr(formData, "sindico_foto_existente");
  const logoSindicoExistente = getStr(formData, "logo_sindico_existente");
  const logoCondominioExistente = getStr(formData, "logo_condominio_existente");

  // Gestor de Atendimento — opcional. O radio 'tem_gestor' diz se o
  // condo tem gestor; se 'nao', todos os campos do gestor sao zerados.
  const temGestor = getStr(formData, "tem_gestor") !== "nao";
  const gestor_nome_raw = getStr(formData, "gestor_nome");
  if (temGestor && !gestor_nome_raw) {
    backWithError(slug, "Marcou que tem gestor — informe o nome do gestor.");
  }
  const gestor_nome = temGestor ? gestor_nome_raw : "";
  const gestorGeneroRaw = getStr(formData, "gestor_genero");
  const gestor_genero: Genero | undefined =
    gestorGeneroRaw === "masculino" || gestorGeneroRaw === "feminino"
      ? gestorGeneroRaw
      : "masculino";
  const gestorFotoExistente = getStr(formData, "gestor_foto_existente");
  const is_by_sindico = getStr(formData, "is_by_sindico") === "on";
  const sindico_email = getStr(formData, "sindico_email");
  const sindico_whatsapp = getStr(formData, "sindico_whatsapp");
  const gestor_email = getStr(formData, "gestor_email");
  const gestor_whatsapp = getStr(formData, "gestor_whatsapp");
  const comunidade_url = getStr(formData, "comunidade_url");
  const comunidadeQrExistente = getStr(formData, "comunidade_qr_existente");
  const mostrar_whatsapp_sindico = getStr(formData, "mostrar_whatsapp_sindico") === "on";
  const mostrar_email_sindico = getStr(formData, "mostrar_email_sindico") === "on";
  // legado: oculta se nenhum dos dois estiver visivel
  const ocultar_contato_sindico = !mostrar_whatsapp_sindico && !mostrar_email_sindico;
  const boasvindasCapaExistente = getStr(formData, "boasvindas_capa_existente");

  const novaFotoSindico = await maybeUploadFoto(formData, "sindico_foto", slug, "sindico");
  const novaFotoGestor = temGestor
    ? await maybeUploadFoto(formData, "gestor_foto", slug, "gestor")
    : null;
  const novoQrComunidade = await maybeUploadFoto(formData, "comunidade_qr", slug, "comunidade-qr");
  const novaCapaBoasVindas = await maybeUploadFoto(formData, "boasvindas_capa", slug, "boasvindas-capa");

  // SEGUNDO sindico (opcional). So salva se tiver nome preenchido.
  const sindico2_nome = getStr(formData, "sindico2_nome");
  const sindico2GeneroRaw = getStr(formData, "sindico2_genero");
  const sindico2_genero: Genero | null = sindico2_nome
    ? (sindico2GeneroRaw === "masculino" || sindico2GeneroRaw === "feminino" || sindico2GeneroRaw === "empresa"
        ? (sindico2GeneroRaw as Genero)
        : null)
    : null;
  const sindico2_email = sindico2_nome ? getStr(formData, "sindico2_email") : "";
  const sindico2_whatsapp = sindico2_nome ? getStr(formData, "sindico2_whatsapp") : "";
  const sindico2FotoExistente = getStr(formData, "sindico2_foto_existente");
  const novaFotoSindico2 = sindico2_nome
    ? await maybeUploadFoto(formData, "sindico2_foto", slug, "sindico2")
    : null;

  // SEGUNDO gestor (opcional). Idem.
  const gestor2_nome = temGestor ? getStr(formData, "gestor2_nome") : "";
  const gestor2GeneroRaw = getStr(formData, "gestor2_genero");
  const gestor2_genero: Genero | null = gestor2_nome
    ? (gestor2GeneroRaw === "masculino" || gestor2GeneroRaw === "feminino"
        ? (gestor2GeneroRaw as Genero)
        : "masculino")
    : null;
  const gestor2_email = gestor2_nome ? getStr(formData, "gestor2_email") : "";
  const gestor2_whatsapp = gestor2_nome ? getStr(formData, "gestor2_whatsapp") : "";
  const gestor2FotoExistente = getStr(formData, "gestor2_foto_existente");
  const novaFotoGestor2 = gestor2_nome
    ? await maybeUploadFoto(formData, "gestor2_foto", slug, "gestor2")
    : null;

  // Equipe de atendimento: ate 5 membros (nome, cargo, foto). Slots
  // sem nome E sem cargo sao descartados. Foto: novo upload sobrescreve,
  // senao mantem a existente.
  const equipe_atendimento: { nome: string; cargo: string; foto_path: string | null }[] = [];
  for (let i = 1; i <= 5; i++) {
    const nm = getStr(formData, `equipe_nome_${i}`);
    const cg = getStr(formData, `equipe_cargo_${i}`);
    if (!nm && !cg) continue;
    const novaFoto = await maybeUploadFoto(formData, `equipe_foto_${i}`, slug, `equipe-${i}`);
    const fotoExist = getStr(formData, `equipe_foto_existente_${i}`);
    equipe_atendimento.push({
      nome: nm,
      cargo: cg,
      foto_path: novaFoto ?? fotoExist ?? null,
    });
  }

  const novoLogoSindico = await maybeUploadLogo(formData, "logo_sindico_file", slug, "sindico");
  const novoLogoCondominio = await maybeUploadLogo(formData, "logo_condominio_file", slug, "condominio");

  const input: CondoMetaInput = {
    nome,
    sindico_nome,
    sindico_genero,
    sindico_foto_path: novaFotoSindico ?? sindicoFotoExistente ?? null,
    sindico_email: sindico_email || null,
    sindico_whatsapp: sindico_whatsapp || null,
    sindico2_nome: sindico2_nome || null,
    sindico2_genero: sindico2_genero,
    sindico2_foto_path: sindico2_nome
      ? (novaFotoSindico2 ?? sindico2FotoExistente ?? null)
      : null,
    sindico2_email: sindico2_email || null,
    sindico2_whatsapp: sindico2_whatsapp || null,
    logo_url: novoLogoSindico ?? logoSindicoExistente ?? null,
    logo_condominio_url:
      novoLogoCondominio ?? logoCondominioExistente ?? null,
    gestor_nome: gestor_nome || null,
    gestor_genero: gestor_nome ? gestor_genero : null,
    gestor_foto_path: gestor_nome
      ? (novaFotoGestor ?? gestorFotoExistente ?? null)
      : null,
    gestor_email: gestor_nome ? gestor_email || null : null,
    gestor_whatsapp: gestor_nome ? gestor_whatsapp || null : null,
    gestor2_nome: gestor2_nome || null,
    gestor2_genero: gestor2_genero,
    gestor2_foto_path: gestor2_nome
      ? (novaFotoGestor2 ?? gestor2FotoExistente ?? null)
      : null,
    gestor2_email: gestor2_email || null,
    gestor2_whatsapp: gestor2_whatsapp || null,
    is_by_sindico,
    comunidade_url: comunidade_url || null,
    comunidade_qrcode_path: novoQrComunidade ?? comunidadeQrExistente ?? null,
    equipe_atendimento: equipe_atendimento.length ? equipe_atendimento : null,
    ocultar_contato_sindico,
    mostrar_whatsapp_sindico,
    mostrar_email_sindico,
    boasvindas_capa_path: novaCapaBoasVindas ?? boasvindasCapaExistente ?? null,
  };

  try {
    await upsertCondoMeta(input);
  } catch (e) {
    const msg = describeError(e);
    if (/relation.*condominios_meta.*does not exist|table.*condominios_meta/i.test(msg)) {
      backWithError(
        slug,
        "Tabela condominios_meta ainda não existe. Rode a migration 20260509 no Supabase.",
      );
    }
    backWithError(slug, `Não foi possível salvar. ${msg}`);
  }

  revalidatePath("/sindicompany/condominios");
  revalidatePath(`/sindicompany/condominios/${slugifyCondo(nome)}`);
  redirect(`/sindicompany/condominios?saved=${slug}`);
}

export async function renomearCondominioAction(formData: FormData): Promise<void> {
  await requireAuth();
  const slug = getStr(formData, "slug");
  const atual = getStr(formData, "condo_nome_atual") || condoFromSlug(slug) || "";
  const novo = getStr(formData, "condo_nome_novo");
  if (!atual) backWithError(slug, "Nao consegui identificar o nome atual do condominio.");
  if (!novo) backWithError(slug, "Informe o novo nome do condominio.");
  if (atual === novo) {
    redirect(`/sindicompany/condominios/${slug}`);
  }
  try {
    await renameCondoMeta(atual, novo);
  } catch (e) {
    backWithError(slug, `Nao foi possivel renomear: ${describeError(e)}`);
  }
  revalidatePath("/sindicompany/condominios");
  revalidatePath(`/sindicompany/condominios/${slug}`);
  const novoSlug = slugifyCondo(novo);
  revalidatePath(`/sindicompany/condominios/${novoSlug}`);
  redirect(`/sindicompany/condominios/${novoSlug}?renamed=1`);
}

export async function copiarEquipeParaTodosAction(formData: FormData): Promise<void> {
  await requireAuth();
  const slug = getStr(formData, "slug");
  const nomeOrigem = getStr(formData, "condo_nome") || condoFromSlug(slug) || "";
  if (!nomeOrigem) backWithError(slug, "Nao consegui identificar o condominio.");
  let resultado: { atualizados: number; criados: number; fonte: string };
  try {
    resultado = await copiarEquipeParaTodosCondos(nomeOrigem, CONDOMINIOS);
  } catch (e) {
    backWithError(slug, `Nao foi possivel copiar a equipe: ${describeError(e)}`);
  }
  revalidatePath("/sindicompany/condominios");
  const total = resultado.atualizados + resultado.criados;
  const msg = `Equipe copiada para ${total} condominio(s). Atualizados: ${resultado.atualizados}; criados: ${resultado.criados}.`;
  redirect(`/sindicompany/condominios/${slug}?equipe_copiada=${encodeURIComponent(msg)}`);
}
