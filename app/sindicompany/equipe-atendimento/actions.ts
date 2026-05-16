"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import {
  createMembroEquipe,
  deleteMembroEquipe,
  uploadFotoMembroEquipe,
} from "@/lib/sindicompany/equipe-atendimento";
import { describeError } from "@/lib/sindicompany/errors";

const MAX_PHOTO_BYTES = 5 * 1024 * 1024;
const EXT_BY_TYPE: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};

async function requireAuth() {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) {
    redirect("/sindicompany/login");
  }
}

function s(fd: FormData, k: string): string {
  return String(fd.get(k) ?? "").trim();
}

function back(error: string): never {
  redirect(`/sindicompany/equipe-atendimento?error=${encodeURIComponent(error)}`);
}

export async function adicionarMembroAction(formData: FormData): Promise<void> {
  await requireAuth();
  const nome = s(formData, "nome");
  const cargo = s(formData, "cargo");
  if (!nome) back("Informe o nome do membro.");
  if (!cargo) back("Informe o cargo.");

  let foto_path: string | null = null;
  const file = formData.get("foto");
  if (file instanceof File && file.size > 0) {
    if (file.size > MAX_PHOTO_BYTES) back("Foto maior que 5MB.");
    const ext = EXT_BY_TYPE[file.type];
    if (!ext) back("Foto precisa ser JPG, PNG ou WebP.");
    try {
      const buf = Buffer.from(await file.arrayBuffer());
      foto_path = await uploadFotoMembroEquipe(buf, file.type, ext);
    } catch (e) {
      back(`Falha ao subir foto: ${describeError(e)}`);
    }
  }

  try {
    await createMembroEquipe({ nome, cargo, foto_path });
  } catch (e) {
    back(`Falha ao cadastrar: ${describeError(e)}`);
  }
  revalidatePath("/sindicompany/equipe-atendimento");
  redirect("/sindicompany/equipe-atendimento?added=1");
}

export async function removerMembroAction(formData: FormData): Promise<void> {
  await requireAuth();
  const id = s(formData, "id");
  if (!id) redirect("/sindicompany/equipe-atendimento");
  try {
    await deleteMembroEquipe(id);
  } catch (e) {
    back(`Falha ao remover: ${describeError(e)}`);
  }
  revalidatePath("/sindicompany/equipe-atendimento");
  redirect("/sindicompany/equipe-atendimento?removed=1");
}
