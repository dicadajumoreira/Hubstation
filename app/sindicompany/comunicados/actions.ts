"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { createComunicado } from "@/lib/sindicompany/comunicados";

async function requireAuth() {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) {
    redirect("/sindicompany/login");
  }
}

function s(fd: FormData, k: string): string {
  return String(fd.get(k) ?? "").trim();
}

export async function criarComunicadoAction(formData: FormData): Promise<void> {
  await requireAuth();
  const condominio = s(formData, "condominio");
  const titulo = s(formData, "titulo");
  if (!condominio || !titulo) {
    redirect("/sindicompany/comunicados/novo?error=" + encodeURIComponent("Informe o condomínio e o título."));
  }
  const c = await createComunicado({
    condominio,
    titulo,
    subtitulo: s(formData, "subtitulo") || null,
    briefing: s(formData, "briefing") || null,
    corpo: s(formData, "corpo") || "",
  });
  revalidatePath("/sindicompany/comunicados");
  redirect(`/sindicompany/comunicados/${c.id}`);
}
