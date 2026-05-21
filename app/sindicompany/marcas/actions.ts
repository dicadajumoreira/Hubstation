"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { createMarca, updateMarca } from "@/lib/sindicompany/marcas-db";

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
    });
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

  try {
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
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Falha ao salvar.";
    redirect(`${back}?error=${encodeURIComponent(msg)}`);
  }
  revalidatePath("/sindicompany/marcas");
  redirect("/sindicompany/marcas");
}
