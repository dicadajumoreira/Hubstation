"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  deleteComunicado,
  gerarTextoComunicado,
  getComunicado,
  updateComunicado,
  uploadComunicadoIlustracao,
} from "@/lib/sindicompany/comunicados";
import { describeError } from "@/lib/sindicompany/errors";

const MAX_IMG_BYTES = 6 * 1024 * 1024;
const EXT_BY_TYPE: Record<string, string> = {
  "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/svg+xml": "svg",
};

async function requireAuth() {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) redirect("/sindicompany/login");
}

function s(fd: FormData, k: string): string {
  return String(fd.get(k) ?? "").trim();
}

function back(id: string, error: string): never {
  redirect(`/sindicompany/comunicados/${id}?error=${encodeURIComponent(error)}`);
}

export async function salvarComunicadoAction(formData: FormData): Promise<void> {
  await requireAuth();
  const id = s(formData, "id");
  if (!id) redirect("/sindicompany/comunicados");
  const titulo = s(formData, "titulo");
  if (!titulo) back(id, "Informe o título.");
  try {
    await updateComunicado(id, {
      condominio: s(formData, "condominio") || undefined,
      titulo,
      subtitulo: s(formData, "subtitulo") || null,
      briefing: s(formData, "briefing") || null,
      corpo: s(formData, "corpo"),
    });
  } catch (e) {
    back(id, `Não foi possível salvar. ${describeError(e)}`);
  }
  revalidatePath(`/sindicompany/comunicados/${id}`);
  redirect(`/sindicompany/comunicados/${id}?saved=1`);
}

export async function gerarTextoComIaAction(formData: FormData): Promise<void> {
  await requireAuth();
  const id = s(formData, "id");
  if (!id) redirect("/sindicompany/comunicados");
  const c = await getComunicado(id).catch(() => null);
  if (!c) redirect("/sindicompany/comunicados");
  const briefing = s(formData, "briefing") || c.briefing || "";
  if (!briefing) back(id, "Escreva um briefing para gerar o texto.");
  const r = await gerarTextoComunicado({
    condominio: c.condominio,
    titulo: c.titulo,
    subtitulo: c.subtitulo,
    briefing,
  });
  if (!r.ok) back(id, r.error);
  try {
    await updateComunicado(id, { briefing, corpo: r.texto });
  } catch (e) {
    back(id, `Texto gerado, mas não consegui salvar. ${describeError(e)}`);
  }
  revalidatePath(`/sindicompany/comunicados/${id}`);
  redirect(`/sindicompany/comunicados/${id}?gerado=1`);
}

export async function uploadIlustracaoAction(formData: FormData): Promise<void> {
  await requireAuth();
  const id = s(formData, "id");
  if (!id) redirect("/sindicompany/comunicados");
  const file = formData.get("ilustracao");
  if (!(file instanceof File) || file.size === 0) back(id, "Selecione um arquivo de imagem.");
  if (file.size > MAX_IMG_BYTES) back(id, "Imagem maior que 6MB.");
  const ext = EXT_BY_TYPE[file.type];
  if (!ext) back(id, "Use JPG, PNG, WebP ou SVG.");
  try {
    const buf = Buffer.from(await file.arrayBuffer());
    const path = await uploadComunicadoIlustracao(id, buf, file.type, ext);
    await updateComunicado(id, { ilustracao_path: path });
  } catch (e) {
    back(id, `Falha ao subir a ilustração. ${describeError(e)}`);
  }
  revalidatePath(`/sindicompany/comunicados/${id}`);
  redirect(`/sindicompany/comunicados/${id}?ilustracao=1`);
}

export async function removerIlustracaoAction(formData: FormData): Promise<void> {
  await requireAuth();
  const id = s(formData, "id");
  if (!id) redirect("/sindicompany/comunicados");
  try {
    await updateComunicado(id, { ilustracao_path: null });
  } catch (e) {
    back(id, `Não foi possível remover. ${describeError(e)}`);
  }
  revalidatePath(`/sindicompany/comunicados/${id}`);
  redirect(`/sindicompany/comunicados/${id}`);
}

export async function excluirComunicadoAction(formData: FormData): Promise<void> {
  await requireAuth();
  const id = s(formData, "id");
  if (!id) redirect("/sindicompany/comunicados");
  try {
    await deleteComunicado(id);
  } catch (e) {
    back(id, `Não foi possível excluir. ${describeError(e)}`);
  }
  revalidatePath("/sindicompany/comunicados");
  redirect("/sindicompany/comunicados");
}
