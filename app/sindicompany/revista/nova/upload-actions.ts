"use server";

import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { slugifyCondo } from "@/lib/sindicompany/condominios";
import {
  copyAssetsToByBrand,
  createByIconCarrosselUploadIntent,
  createByIconUploadIntent,
  createByLogoUploadIntent,
  createByPatternUploadIntent,
  createConsvictaIconCarrosselUploadIntent,
  createConsvictaIconUploadIntent,
  createConsvictaLogoUploadIntent,
  createConsvictaPatternUploadIntent,
  createEventosZipUploadIntent,
  createIconCarrosselUploadIntent,
  createIconUploadIntent,
  createLogoUploadIntent,
  createManutencaoCapaUploadIntent,
  createManutencaoZipUploadIntent,
  createPatternUploadIntent,
  createPrestacaoUploadIntent,
  ICON_CARROSSEL_MAX_SLOTS,
  ICON_MAX_SLOTS,
  LOGO_MAX_SLOTS,
  PATTERN_MAX_SLOTS,
} from "@/lib/sindicompany/condominios-db";

const ALLOWED_PRESTACAO_EXT = new Set(["jpg", "jpeg", "png", "webp", "pdf"]);
const ALLOWED_IMG_EXT = new Set(["jpg", "jpeg", "png", "webp"]);
const ALLOWED_VECTOR_EXT = new Set(["jpg", "jpeg", "png", "webp", "svg"]);

async function requireAuth() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    throw new Error("unauthorized");
  }
}

interface UploadIntentResult {
  ok: true;
  uploadUrl: string;  // signed PUT URL
  token: string;
  path: string;
  publicUrl: string;
}

interface UploadIntentError {
  ok: false;
  error: string;
}

export async function getPrestacaoUploadIntent(
  condominio: string,
  ext: string,
): Promise<UploadIntentResult | UploadIntentError> {
  try {
    await requireAuth();
  } catch {
    return { ok: false, error: "Sessão expirada. Faça login de novo." };
  }
  const e = ext.toLowerCase().replace(/^\./, "");
  if (!ALLOWED_PRESTACAO_EXT.has(e)) {
    return { ok: false, error: "Extensão precisa ser jpg, png, webp ou pdf." };
  }
  if (!condominio) return { ok: false, error: "Condomínio inválido." };
  try {
    const slug = slugifyCondo(condominio);
    const id = `pending-${Date.now()}`;
    const intent = await createPrestacaoUploadIntent(slug, id, e);
    // Constrói a URL completa do PUT a partir do supabase storage URL
    const baseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const uploadUrl = `${baseUrl}/storage/v1/object/upload/sign/condominios-fotos/${intent.path}?token=${intent.token}`;
    return {
      ok: true,
      uploadUrl,
      token: intent.token,
      path: intent.path,
      publicUrl: intent.publicUrl,
    };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Falha desconhecida." };
  }
}

export async function getManutencaoZipUploadIntent(
  condominio: string,
): Promise<UploadIntentResult | UploadIntentError> {
  try {
    await requireAuth();
  } catch {
    return { ok: false, error: "Sessão expirada. Faça login de novo." };
  }
  if (!condominio) return { ok: false, error: "Condomínio inválido." };
  try {
    const slug = slugifyCondo(condominio);
    const id = `pending-${Date.now()}`;
    const intent = await createManutencaoZipUploadIntent(slug, id);
    const baseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const uploadUrl = `${baseUrl}/storage/v1/object/upload/sign/condominios-fotos/${intent.path}?token=${intent.token}`;
    return {
      ok: true,
      uploadUrl,
      token: intent.token,
      path: intent.path,
      publicUrl: intent.publicUrl,
    };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Falha desconhecida." };
  }
}

export async function getEventosZipUploadIntent(
  condominio: string,
): Promise<UploadIntentResult | UploadIntentError> {
  try {
    await requireAuth();
  } catch {
    return { ok: false, error: "Sessão expirada. Faça login de novo." };
  }
  if (!condominio) return { ok: false, error: "Condomínio inválido." };
  try {
    const slug = slugifyCondo(condominio);
    const id = `pending-${Date.now()}`;
    const intent = await createEventosZipUploadIntent(slug, id);
    const baseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const uploadUrl = `${baseUrl}/storage/v1/object/upload/sign/condominios-fotos/${intent.path}?token=${intent.token}`;
    return {
      ok: true,
      uploadUrl,
      token: intent.token,
      path: intent.path,
      publicUrl: intent.publicUrl,
    };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Falha desconhecida." };
  }
}

export async function getManutencaoCapaUploadIntent(
  condominio: string,
  ext: string,
): Promise<UploadIntentResult | UploadIntentError> {
  try {
    await requireAuth();
  } catch {
    return { ok: false, error: "Sessão expirada. Faça login de novo." };
  }
  const e = ext.toLowerCase().replace(/^\./, "");
  if (!ALLOWED_IMG_EXT.has(e)) {
    return { ok: false, error: "Capa precisa ser jpg, png ou webp." };
  }
  if (!condominio) return { ok: false, error: "Condomínio inválido." };
  try {
    const slug = slugifyCondo(condominio);
    const id = `pending-${Date.now()}`;
    const intent = await createManutencaoCapaUploadIntent(slug, id, e);
    const baseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const uploadUrl = `${baseUrl}/storage/v1/object/upload/sign/condominios-fotos/${intent.path}?token=${intent.token}`;
    return {
      ok: true,
      uploadUrl,
      token: intent.token,
      path: intent.path,
      publicUrl: intent.publicUrl,
    };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Falha desconhecida." };
  }
}

export async function getPatternUploadIntent(
  slot: number,
  ext: string,
): Promise<UploadIntentResult | UploadIntentError> {
  try {
    await requireAuth();
  } catch {
    return { ok: false, error: "Sessao expirada. Faca login de novo." };
  }
  if (!Number.isInteger(slot) || slot < 1 || slot > 20) {
    return { ok: false, error: "Slot invalido (1 a 20)." };
  }
  const e = ext.toLowerCase().replace(/^\./, "");
  if (!ALLOWED_IMG_EXT.has(e)) {
    return { ok: false, error: "Pattern precisa ser jpg, png ou webp." };
  }
  try {
    const intent = await createPatternUploadIntent(slot, e);
    const baseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const uploadUrl = `${baseUrl}/storage/v1/object/upload/sign/condominios-fotos/${intent.path}?token=${intent.token}`;
    return {
      ok: true,
      uploadUrl,
      token: intent.token,
      path: intent.path,
      publicUrl: intent.publicUrl,
    };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Falha desconhecida." };
  }
}

async function _slotIntent(
  ext: string,
  slot: number,
  max: number,
  label: string,
  create: (s: number, e: string) => Promise<{ token: string; path: string; publicUrl: string }>,
): Promise<UploadIntentResult | UploadIntentError> {
  try {
    await requireAuth();
  } catch {
    return { ok: false, error: "Sessao expirada. Faca login de novo." };
  }
  if (!Number.isInteger(slot) || slot < 1 || slot > max) {
    return { ok: false, error: `Slot invalido (1 a ${max}).` };
  }
  const e = ext.toLowerCase().replace(/^\./, "");
  if (!ALLOWED_VECTOR_EXT.has(e)) {
    return { ok: false, error: `${label} precisa ser jpg, png, webp ou svg.` };
  }
  try {
    const intent = await create(slot, e);
    const baseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const uploadUrl = `${baseUrl}/storage/v1/object/upload/sign/condominios-fotos/${intent.path}?token=${intent.token}`;
    return {
      ok: true,
      uploadUrl,
      token: intent.token,
      path: intent.path,
      publicUrl: intent.publicUrl,
    };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Falha desconhecida." };
  }
}

export async function getIconUploadIntent(slot: number, ext: string) {
  return _slotIntent(ext, slot, ICON_MAX_SLOTS, "Icon", createIconUploadIntent);
}

export async function getIconCarrosselUploadIntent(slot: number, ext: string) {
  return _slotIntent(
    ext,
    slot,
    ICON_CARROSSEL_MAX_SLOTS,
    "Icon Carrossel",
    createIconCarrosselUploadIntent,
  );
}

export async function getLogoUploadIntent(slot: number, ext: string) {
  return _slotIntent(ext, slot, LOGO_MAX_SLOTS, "Logo", createLogoUploadIntent);
}

// --- Assets BySindicompany ---

export async function getByPatternUploadIntent(slot: number, ext: string) {
  return _slotIntent(
    ext, slot, PATTERN_MAX_SLOTS, "Pattern (By)", createByPatternUploadIntent,
  );
}
export async function getByIconUploadIntent(slot: number, ext: string) {
  return _slotIntent(
    ext, slot, ICON_MAX_SLOTS, "Icon (By)", createByIconUploadIntent,
  );
}
export async function getByIconCarrosselUploadIntent(slot: number, ext: string) {
  return _slotIntent(
    ext, slot, ICON_CARROSSEL_MAX_SLOTS, "Fundo Carrossel (By)",
    createByIconCarrosselUploadIntent,
  );
}
export async function getByLogoUploadIntent(slot: number, ext: string) {
  return _slotIntent(
    ext, slot, LOGO_MAX_SLOTS, "Logo (By)", createByLogoUploadIntent,
  );
}

// --- Assets Consvicta ---

export async function getConsvictaPatternUploadIntent(slot: number, ext: string) {
  return _slotIntent(
    ext, slot, PATTERN_MAX_SLOTS, "Pattern (Consvicta)", createConsvictaPatternUploadIntent,
  );
}
export async function getConsvictaIconUploadIntent(slot: number, ext: string) {
  return _slotIntent(
    ext, slot, ICON_MAX_SLOTS, "Icon (Consvicta)", createConsvictaIconUploadIntent,
  );
}
export async function getConsvictaIconCarrosselUploadIntent(slot: number, ext: string) {
  return _slotIntent(
    ext, slot, ICON_CARROSSEL_MAX_SLOTS, "Fundo Carrossel (Consvicta)",
    createConsvictaIconCarrosselUploadIntent,
  );
}
export async function getConsvictaLogoUploadIntent(slot: number, ext: string) {
  return _slotIntent(
    ext, slot, LOGO_MAX_SLOTS, "Logo (Consvicta)", createConsvictaLogoUploadIntent,
  );
}

/** Copia Patterns, Icons, Fundo Carrossel e Logotipos do @sindicompanybr
 *  pros buckets do @bysindicompany. Idempotente — pode rodar de novo. */
export async function copiarAssetsParaBy(): Promise<
  { ok: true; resumo: string } | { ok: false; error: string }
> {
  try {
    await requireAuth();
  } catch {
    return { ok: false, error: "Sessao expirada. Faca login de novo." };
  }
  const r = await copyAssetsToByBrand();
  if (!r.ok) return r;
  const partes = Object.entries(r.copied).map(
    ([k, n]) => `${k.replace("__", "")}: ${n}`,
  );
  return { ok: true, resumo: partes.join(" · ") };
}
