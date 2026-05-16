"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  parseMesAno,
  upsertEditorial,
  uploadEditorialFotoCapa,
  type EditorialInput,
} from "@/lib/sindicompany/editoriais";
import { describeError, detectMigrationMissing } from "@/lib/sindicompany/errors";

const MAX_PHOTO_BYTES = 8 * 1024 * 1024; // 8MB
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
  redirect(`/sindicompany/editorial/${slug}?${params.toString()}`);
}

function getStr(fd: FormData, key: string): string {
  return String(fd.get(key) ?? "").trim();
}

function isValidImageUrl(url: string): boolean {
  if (!url) return true;
  return /^https?:\/\//.test(url);
}

export async function salvarEditorialAction(formData: FormData): Promise<void> {
  await requireAuth();

  const slug = getStr(formData, "slug");
  const parsed = parseMesAno(slug);
  if (!parsed) {
    redirect("/sindicompany/editorial");
  }

  // Foto de capa: novo upload (file) sobrescreve; senão mantém a existente.
  const fotoExistente = getStr(formData, "foto_capa_existente");
  let foto_capa_url = fotoExistente;

  const fotoFile = formData.get("foto_capa_file");
  if (fotoFile instanceof File && fotoFile.size > 0) {
    if (fotoFile.size > MAX_PHOTO_BYTES) {
      backWithError(slug, "Foto de capa maior que 8MB.");
    }
    if (!ALLOWED_TYPES.has(fotoFile.type)) {
      backWithError(slug, "Foto de capa precisa ser JPG, PNG ou WebP.");
    }
    try {
      const buf = Buffer.from(await fotoFile.arrayBuffer());
      const ext = EXT_BY_TYPE[fotoFile.type];
      foto_capa_url = await uploadEditorialFotoCapa(
        parsed.mes,
        parsed.ano,
        buf,
        fotoFile.type,
        ext,
      );
    } catch (e) {
      console.error("[editorial] upload foto failed:", e);
      const msg = describeError(e);
      if (/bucket.*not.*found|not.*found.*bucket/i.test(msg)) {
        backWithError(slug, "Bucket editoriais-fotos não existe. Rode a migration 20260512.");
      }
      backWithError(slug, `Falha ao subir foto: ${msg}`);
    }
  }

  if (foto_capa_url && !isValidImageUrl(foto_capa_url)) {
    backWithError(slug, "URL de foto de capa inválida.");
  }

  const input: EditorialInput = {
    mes: parsed.mes,
    ano: parsed.ano,
    materia_capa_titulo: getStr(formData, "materia_capa_titulo") || undefined,
    materia_capa_subtitulo: getStr(formData, "materia_capa_subtitulo") || undefined,
    foto_capa_url: foto_capa_url || undefined,
    receita_titulo: getStr(formData, "receita_titulo") || undefined,
    receita_descricao: getStr(formData, "receita_descricao") || undefined,
    carta_sindico_tema: getStr(formData, "carta_sindico_tema") || undefined,
    carta_gestor_tema: getStr(formData, "carta_gestor_tema") || undefined,
    notas_editor_geral: getStr(formData, "notas_editor_geral") || undefined,
  };

  try {
    await upsertEditorial(input);
  } catch (e) {
    console.error("[editorial] upsert failed:", e);
    const msg = describeError(e);
    const hint = detectMigrationMissing(msg);
    backWithError(slug, hint ?? `Não foi possível salvar. ${msg}`);
  }

  revalidatePath("/sindicompany/editorial");
  revalidatePath(`/sindicompany/editorial/${slug}`);
  redirect(`/sindicompany/editorial?saved=${slug}`);
}
