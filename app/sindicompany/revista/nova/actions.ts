"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { isCondominioValido, slugifyCondo } from "@/lib/sindicompany/condominios";
import {
  getCondoFotoPublicUrl,
  getCondoMeta,
  gestorTitulo,
} from "@/lib/sindicompany/condominios-db";
import { createRevista, type RevistaInput } from "@/lib/sindicompany/db";
import { getEditorial, editorialEstaPronto } from "@/lib/sindicompany/editoriais";
import { dispatchGenerateRevista } from "@/lib/sindicompany/engine";
import { describeError, detectMigrationMissing } from "@/lib/sindicompany/errors";

const MAX_PHOTO_BYTES = 5 * 1024 * 1024; // 5MB
const ALLOWED_PHOTO_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const PHOTO_EXT_BY_TYPE: Record<string, string> = {
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

function backToFormWithError(message: string, fields: FormData): never {
  const params = new URLSearchParams({ error: message });
  // Preserva os valores que ela já tinha digitado pra ela não perder no erro
  for (const [k, v] of fields.entries()) {
    if (typeof v === "string" && v) params.set(k, v);
  }
  redirect(`/sindicompany/revista/nova?${params.toString()}`);
}

function isValidDriveUrl(url: string): boolean {
  if (!url) return true; // opcional
  return /^https?:\/\/(drive|docs)\.google\.com\//.test(url);
}

function getStr(fd: FormData, key: string): string {
  return String(fd.get(key) ?? "").trim();
}

function getBool(fd: FormData, key: string): boolean {
  const v = fd.get(key);
  return v === "on" || v === "true" || v === "1";
}

export async function novaRevistaAction(formData: FormData): Promise<void> {
  await requireAuth();

  const condominio = getStr(formData, "condominio");
  const mesRaw = getStr(formData, "mes");
  const anoRaw = getStr(formData, "ano");

  if (!condominio) {
    backToFormWithError("Condomínio inválido.", formData);
  }

  const mes = Number.parseInt(mesRaw, 10);
  const ano = Number.parseInt(anoRaw, 10);
  if (!Number.isInteger(mes) || mes < 1 || mes > 12) {
    backToFormWithError("Mês inválido.", formData);
  }
  if (!Number.isInteger(ano) || ano < 2025 || ano > 2030) {
    backToFormWithError("Ano inválido.", formData);
  }

  // Liderança vem do cadastro do condomínio (condominios_meta).
  const meta = await getCondoMeta(condominio).catch(() => null);
  // Aceita o condominio se estiver na lista canonica OU se tiver
  // cadastro no banco (condominios novos vivem so no condominios_meta).
  if (!isCondominioValido(condominio) && !meta) {
    backToFormWithError(
      `Condomínio "${condominio}" não encontrado. Cadastre-o em Condomínios primeiro.`,
      formData,
    );
  }
  if (!meta || !meta.sindico_nome || !meta.sindico_genero) {
    backToFormWithError(
      `Cadastre o(a) síndico(a) de "${condominio}" antes de gerar a revista. ` +
        `Vá em Condomínios → ${condominio}.`,
      formData,
    );
  }
  const sindico_nome = meta.sindico_nome;
  const sindico_genero = meta.sindico_genero;

  // Gestor de Atendimento agora vem do CADASTRO DO CONDOMÍNIO (tela
  // Condomínios), não mais do form da revista. Se o condo não tem
  // gestor cadastrado, a carta do gestor não sai na edição.
  const tem_gestor = !!(meta.gestor_nome && meta.gestor_nome.trim());
  const gestor_nome = tem_gestor ? (meta.gestor_nome ?? undefined) : undefined;
  const gestor_titulo = tem_gestor ? gestorTitulo(meta.gestor_genero) : undefined;
  const gestor_foto_url =
    tem_gestor && meta.gestor_foto_path
      ? getCondoFotoPublicUrl(meta.gestor_foto_path)
      : undefined;

  // drive_manutencao_url legado: aceito ainda pra revistas antigas, mas o
  // form novo usa ZIP. drive_prestacao_url removido.
  const drive_manutencao_url = getStr(formData, "drive_manutencao_url");
  if (drive_manutencao_url && !isValidDriveUrl(drive_manutencao_url)) {
    backToFormWithError("Link de manutenção precisa ser uma URL do Google Drive.", formData);
  }

  const tem_advertencias = getBool(formData, "tem_advertencias");
  const multas_advertencias_obs = getStr(formData, "multas_advertencias_obs");

  const tem_eventos = getBool(formData, "tem_eventos");
  const eventos_zip_url =
    getStr(formData, "eventos_zip_url_uploaded") || undefined;

  const foto_capa_clara = getBool(formData, "foto_capa_clara");

  const notas_editor = getStr(formData, "notas_editor");
  const carta_sindico_texto = getStr(formData, "carta_sindico_texto");
  const carta_gestor_texto = getStr(formData, "carta_gestor_texto");

  // Editorial mensal precisa estar pronto antes de gerar revista.
  const editorial = await getEditorial(mes, ano).catch(() => null);
  if (!editorialEstaPronto(editorial)) {
    const slug = `${String(mes).padStart(2, "0")}-${ano}`;
    backToFormWithError(
      `Editorial de ${mesRaw}/${anoRaw} ainda não está pronto. ` +
        `Defina matéria de capa e receita em Editorial mensal (/sindicompany/editorial/${slug}).`,
      formData,
    );
  }

  // Os arquivos (ZIP de manutenção, dashboard de prestação) são subidos
  // direto do navegador pro Supabase Storage via signed URL. O form só
  // recebe a URL pública resultante. Isso evita o limite de body do
  // Server Action (Vercel cap em 4.5MB-50MB).
  const manutencao_zip_url =
    getStr(formData, "manutencao_zip_url_uploaded") || undefined;
  const manutencao_capa_url =
    getStr(formData, "manutencao_capa_url_uploaded") || undefined;
  const prestacao_arquivo_url =
    getStr(formData, "prestacao_arquivo_url_uploaded") || undefined;

  const input: RevistaInput = {
    condominio,
    mes,
    ano,
    sindico_nome,
    sindico_genero,
    tem_gestor,
    gestor_nome,
    gestor_foto_url,
    gestor_titulo,
    is_by_sindico: !!meta.is_by_sindico,
    foto_capa_clara,
    drive_manutencao_url: drive_manutencao_url || undefined,
    manutencao_zip_url: manutencao_zip_url || undefined,
    manutencao_capa_url: manutencao_capa_url || undefined,
    prestacao_arquivo_url: prestacao_arquivo_url || undefined,
    tem_advertencias,
    multas_advertencias_obs: tem_advertencias ? multas_advertencias_obs : undefined,
    tem_eventos,
    eventos_zip_url: tem_eventos ? eventos_zip_url : undefined,
    notas_editor: notas_editor || undefined,
    carta_sindico_texto: carta_sindico_texto || undefined,
    // Carta do gestor só salva se o condo tem gestor cadastrado
    carta_gestor_texto: tem_gestor ? carta_gestor_texto || undefined : undefined,
  };

  let revista;
  try {
    revista = await createRevista(input);
  } catch (e) {
    console.error("[revista] createRevista failed:", e);
    const msg = describeError(e);
    if (msg.toLowerCase().includes("duplicate")) {
      backToFormWithError("Já existe uma revista para esse condomínio nesse mês.", formData);
    }
    const migrationHint = detectMigrationMissing(msg);
    backToFormWithError(
      migrationHint ? migrationHint : `Não foi possível criar a edição. ${msg}`,
      formData,
    );
  }

  // Dispara a engine via GitHub Actions (fire-and-forget). Se falhar
  // ou demorar demais, a editora pode subir o PDF manualmente na página
  // da revista como fallback.
  await dispatchGenerateRevista(revista.id);

  revalidatePath("/sindicompany/dashboard");
  redirect(`/sindicompany/revista/${revista.id}`);
}
