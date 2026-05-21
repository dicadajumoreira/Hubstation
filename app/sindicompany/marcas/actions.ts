"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  createMarca,
  updateMarca,
  type MarcaTipografia,
} from "@/lib/sindicompany/marcas-db";
import { processFontZips } from "@/lib/sindicompany/marca-fonts";
import { uploadMarcaAssets } from "@/lib/sindicompany/marca-assets";

async function requireAuth() {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) {
    redirect("/sindicompany/login");
  }
}

function s(fd: FormData, k: string): string {
  return String(fd.get(k) ?? "").trim();
}

// textarea com um item por linha -> string[] (descarta linhas vazias)
function lines(fd: FormData, k: string): string[] {
  return s(fd, k)
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
}

// Chaves de cor que o template do engine usa.
const PALETA_KEYS = ["onix", "mint", "sand", "lavender", "purple", "white", "gray_5"];

// Monta o objeto de paleta a partir dos inputs paleta_<chave>. So aceita
// HEX #rrggbb; chave invalida/vazia e descartada. Vazio -> null (usa o tema
// base no engine).
function paletaFromForm(fd: FormData): Record<string, string> | null {
  const out: Record<string, string> = {};
  for (const k of PALETA_KEYS) {
    const v = s(fd, `paleta_${k}`).toLowerCase();
    if (/^#[0-9a-f]{6}$/.test(v)) out[k] = v;
  }
  return Object.keys(out).length ? out : null;
}

// Le o ZIP de fontes (campo fontes_zip) + os nomes de familia e devolve a
// tipografia pronta. undefined = nenhum zip enviado (nao mexe na tipografia
// existente). Lanca Error amigavel em caso de problema no zip.
async function tipografiaFromForm(
  fd: FormData,
  bucketPrefix: string,
): Promise<MarcaTipografia | undefined> {
  const files = fd
    .getAll("fontes_zip")
    .filter((f): f is File => f instanceof File && f.size > 0);
  if (files.length === 0) return undefined;
  const zips = await Promise.all(
    files.map(async (f) => new Uint8Array(await f.arrayBuffer())),
  );
  const { tipografia } = await processFontZips(zips, bucketPrefix, {
    display: s(fd, "fonte_display"),
    body: s(fd, "fonte_body"),
    numeric: s(fd, "fonte_numeric"),
  });
  return tipografia;
}

// slug url-safe: minusculas, sem acento, so [a-z0-9-]
function normalizeSlug(raw: string): string {
  return raw
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export async function criarMarcaAction(formData: FormData): Promise<void> {
  await requireAuth();
  const back = "/sindicompany/marcas/novo";
  const fail = (msg: string) =>
    redirect(`${back}?error=${encodeURIComponent(msg)}`);

  const nome = s(formData, "nome");
  const slug = normalizeSlug(s(formData, "slug"));
  const handle = s(formData, "handle");
  if (!nome || !slug || !handle) {
    fail("Informe pelo menos nome, slug e handle.");
  }
  const bucketPrefix = s(formData, "bucket_prefix") || `__${slug}-`;
  const routeSlug = normalizeSlug(s(formData, "route_slug") || `${slug}-assets`);
  const ordemRaw = parseInt(s(formData, "ordem"), 10);

  try {
    const tipografia = await tipografiaFromForm(formData, bucketPrefix);
    await createMarca({
      slug,
      nome,
      handle,
      nicho: s(formData, "nicho") || null,
      bucketPrefix,
      routeSlug,
      ativo: formData.get("ativo") != null,
      ordem: Number.isFinite(ordemRaw) ? ordemRaw : 0,
      persona: s(formData, "persona") || null,
      assinatura: s(formData, "assinatura") || null,
      temasSugeridos: lines(formData, "temas"),
      paleta: paletaFromForm(formData),
      tipografia: tipografia ?? null,
    });
    await uploadMarcaAssets(formData, bucketPrefix);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Falha ao criar marca.";
    fail(msg.includes("duplicate") ? `Já existe uma marca com o slug "${slug}".` : msg);
  }
  revalidatePath("/sindicompany/marcas");
  redirect("/sindicompany/marcas");
}

export async function atualizarMarcaAction(formData: FormData): Promise<void> {
  await requireAuth();
  const slug = s(formData, "slug");
  const back = `/sindicompany/marcas/${slug}`;
  if (!slug) redirect("/sindicompany/marcas");

  const nome = s(formData, "nome");
  const handle = s(formData, "handle");
  if (!nome || !handle) {
    redirect(`${back}?error=${encodeURIComponent("Nome e handle são obrigatórios.")}`);
  }
  const ordemRaw = parseInt(s(formData, "ordem"), 10);
  const prefix = s(formData, "bucket_prefix") || `__${slug}-`;

  try {
    // So mexe na tipografia se um novo zip foi enviado; senao mantem a atual.
    const tipografia = await tipografiaFromForm(formData, prefix);
    await updateMarca(slug, {
      nome,
      handle,
      nicho: s(formData, "nicho") || null,
      bucketPrefix: s(formData, "bucket_prefix"),
      routeSlug: normalizeSlug(s(formData, "route_slug")),
      ativo: formData.get("ativo") != null,
      ordem: Number.isFinite(ordemRaw) ? ordemRaw : 0,
      persona: s(formData, "persona") || null,
      assinatura: s(formData, "assinatura") || null,
      temasSugeridos: lines(formData, "temas"),
      paleta: paletaFromForm(formData),
      ...(tipografia ? { tipografia } : {}),
    });
    await uploadMarcaAssets(formData, prefix);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Falha ao salvar.";
    redirect(`${back}?error=${encodeURIComponent(msg)}`);
  }
  revalidatePath("/sindicompany/marcas");
  redirect("/sindicompany/marcas");
}
