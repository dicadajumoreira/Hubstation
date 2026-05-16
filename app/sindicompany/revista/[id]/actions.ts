"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { markRevistaErro, markRevistaPublished, uploadRevistaPdf } from "@/lib/sindicompany/db";
import { dispatchGenerateRevista } from "@/lib/sindicompany/engine";
import { describeError } from "@/lib/sindicompany/errors";

const MAX_PDF_BYTES = 50 * 1024 * 1024; // 50MB

async function requireAuth() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }
}

export async function cancelarRevistaAction(formData: FormData): Promise<void> {
  await requireAuth();
  const id = String(formData.get("id") ?? "").trim();
  if (!id) return;

  try {
    await markRevistaErro(id, "Cancelada manualmente.");
  } catch (e) {
    console.error("[revista] cancelar failed:", e);
    redirect(`/sindicompany/revista/${id}?error=${encodeURIComponent(describeError(e))}`);
  }

  revalidatePath(`/sindicompany/revista/${id}`);
  revalidatePath("/sindicompany/dashboard");
  redirect(`/sindicompany/revista/${id}`);
}

function backWithError(id: string, message: string): never {
  redirect(`/sindicompany/revista/${id}?error=${encodeURIComponent(message)}`);
}

export async function uploadRevistaPdfAction(formData: FormData): Promise<void> {
  await requireAuth();
  const id = String(formData.get("id") ?? "").trim();
  if (!id) return;

  const file = formData.get("pdf");
  if (!(file instanceof File) || file.size === 0) {
    backWithError(id, "Selecione o arquivo PDF antes de enviar.");
  }
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    backWithError(id, "O arquivo precisa ser um PDF.");
  }
  if (file.size > MAX_PDF_BYTES) {
    backWithError(id, `PDF maior que 50MB (${(file.size / 1024 / 1024).toFixed(1)}MB).`);
  }

  const paginasRaw = String(formData.get("paginas") ?? "").trim();
  const paginas = paginasRaw ? Number.parseInt(paginasRaw, 10) : 0;

  try {
    const buf = Buffer.from(await file.arrayBuffer());
    const path = await uploadRevistaPdf(id, buf);
    await markRevistaPublished(id, path, Number.isInteger(paginas) && paginas > 0 ? paginas : 0);
  } catch (e) {
    console.error("[revista] upload failed:", e);
    backWithError(id, `Falha ao subir PDF: ${describeError(e)}`);
  }

  revalidatePath(`/sindicompany/revista/${id}`);
  revalidatePath("/sindicompany/dashboard");
  redirect(`/sindicompany/revista/${id}`);
}

export async function regerarRevistaAction(formData: FormData): Promise<void> {
  await requireAuth();
  const id = String(formData.get("id") ?? "").trim();
  if (!id) return;

  // Reseta o status pra em_producao e dispara o workflow de novo.
  const supabase = createAdminClient();
  const { error } = await supabase
    .from("revistas")
    .update({ status: "em_producao", erro_mensagem: null })
    .eq("id", id);
  if (error) {
    console.error("[revista] regerar reset failed:", error);
    redirect(`/sindicompany/revista/${id}?error=${encodeURIComponent(describeError(error))}`);
  }

  await dispatchGenerateRevista(id);

  revalidatePath(`/sindicompany/revista/${id}`);
  revalidatePath("/sindicompany/dashboard");
  redirect(`/sindicompany/revista/${id}`);
}
