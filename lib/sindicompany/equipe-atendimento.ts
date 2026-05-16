import { createAdminClient } from "@/lib/supabase/admin";

const TABLE = "equipe_atendimento_global";
const BUCKET = "condominios-fotos"; // reaproveita o bucket publico

export interface MembroEquipe {
  id: string;
  nome: string;
  cargo: string;
  foto_path: string | null;
  ordem: number;
  created_at: string;
}

export async function listEquipeAtendimentoGlobal(): Promise<MembroEquipe[]> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .select("*")
    .order("ordem", { ascending: true })
    .order("created_at", { ascending: true });
  if (error) throw error;
  return (data ?? []) as MembroEquipe[];
}

export async function createMembroEquipe(input: {
  nome: string;
  cargo: string;
  foto_path?: string | null;
  ordem?: number;
}): Promise<MembroEquipe> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .insert({
      nome: input.nome,
      cargo: input.cargo,
      foto_path: input.foto_path ?? null,
      ordem: input.ordem ?? 100,
    })
    .select()
    .single();
  if (error) throw error;
  return data as MembroEquipe;
}

export async function deleteMembroEquipe(id: string): Promise<void> {
  const supabase = createAdminClient();
  const { data: m } = await supabase.from(TABLE).select("foto_path").eq("id", id).maybeSingle();
  if (m?.foto_path) {
    await supabase.storage.from(BUCKET).remove([m.foto_path]).catch(() => {});
  }
  const { error } = await supabase.from(TABLE).delete().eq("id", id);
  if (error) throw error;
}

export async function uploadFotoMembroEquipe(
  bytes: Buffer,
  contentType: string,
  ext: string,
): Promise<string> {
  const supabase = createAdminClient();
  const path = `equipe-atendimento/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${ext}`;
  const { error } = await supabase.storage
    .from(BUCKET)
    .upload(path, bytes, { contentType, upsert: true });
  if (error) throw error;
  return path;
}

export function getFotoMembroEquipeUrl(path: string): string {
  const supabase = createAdminClient();
  const { data } = supabase.storage.from(BUCKET).getPublicUrl(path);
  return `${data.publicUrl}?v=${Date.now()}`;
}
