"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { deleteRevista } from "@/lib/sindicompany/db";

async function requireAuth() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }
}

export async function excluirRevistaAction(formData: FormData): Promise<void> {
  await requireAuth();

  const id = String(formData.get("id") ?? "").trim();
  if (!id) return;

  try {
    await deleteRevista(id);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "erro desconhecido";
    redirect(`/sindicompany/dashboard?error=${encodeURIComponent(`Não foi possível excluir: ${msg}`)}`);
  }

  revalidatePath("/sindicompany/dashboard");
  redirect("/sindicompany/dashboard?excluida=1");
}
