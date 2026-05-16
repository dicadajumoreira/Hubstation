import { createAdminClient } from "@/lib/supabase/admin";

export type CarrosselStatus = "rascunho" | "em_producao" | "publicada" | "erro";

export interface CarrosselSlide {
  tipo: string;
  titulo: string;
  body: string;
}

export interface CarrosselCopy {
  slides: CarrosselSlide[];
  legenda: string;
}

export type CarrosselBrand = "sindicompanybr" | "bysindicompany" | "consvictabr";

export const CARROSSEL_BRANDS: { id: CarrosselBrand; handle: string; label: string }[] = [
  { id: "sindicompanybr", handle: "@sindicompanybr", label: "Sindicompany" },
  { id: "bysindicompany", handle: "@bysindicompany", label: "BySindicompany" },
  { id: "consvictabr", handle: "@consvictabr", label: "Consvicta" },
];

export interface Carrossel {
  id: string;
  brand: CarrosselBrand;
  objetivo: string | null;
  titulo: string;
  tema: string | null;
  formato: string | null;
  briefing: string | null;
  foto_capa_url: string | null;
  n_slides: number;
  status: CarrosselStatus;
  png_paths: string[] | null;
  zip_url: string | null;
  slide_fotos: string[] | null;
  legenda: string | null;
  erro_mensagem: string | null;
  gerado_em: string | null;
  copy_options: CarrosselCopy[] | null;
  copy_selected: number | null;
  created_at: string;
  updated_at: string;
}

export interface CarrosselInput {
  brand?: CarrosselBrand;
  objetivo?: string;
  titulo: string;
  tema?: string;
  formato?: string;
  briefing?: string;
  foto_capa_url?: string;
  n_slides?: number;
}

export async function updateCarrossel(
  id: string,
  patch: Partial<{
    foto_capa_url: string;
    copy_options: CarrosselCopy[];
    copy_selected: number | null;
    slide_fotos: (string | null)[];
    status: CarrosselStatus;
  }>,
): Promise<void> {
  const supabase = createAdminClient();
  const { error } = await supabase
    .from(TABLE)
    .update(patch)
    .eq("id", id);
  if (error) throw error;
}

const TABLE = "carrosseis";
const BUCKET = "condominios-fotos"; // reaproveita o bucket público

export async function listCarrosseis(): Promise<Carrossel[]> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .select("*")
    .order("created_at", { ascending: false });
  if (error) throw error;
  return (data ?? []) as Carrossel[];
}

export async function getCarrossel(id: string): Promise<Carrossel | null> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return (data ?? null) as Carrossel | null;
}

export async function createCarrossel(input: CarrosselInput): Promise<Carrossel> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .insert({
      ...input,
      brand: input.brand ?? "sindicompanybr",
      status: "rascunho" as CarrosselStatus,
    })
    .select()
    .single();
  if (error) throw error;
  return data as Carrossel;
}

export async function deleteCarrossel(id: string): Promise<void> {
  const supabase = createAdminClient();
  const { error } = await supabase.from(TABLE).delete().eq("id", id);
  if (error) throw error;
}

/** Upload da foto de capa do carrossel via signed URL. Path fixo
 *  no bucket público condominios-fotos pra reaproveitar a infra. */
export async function createCarrosselFotoUploadIntent(
  ext: string,
): Promise<{ token: string; path: string; publicUrl: string }> {
  const e = ext.toLowerCase().replace(/^\./, "");
  const path = `__carrosseis/foto-${Date.now()}.${e}`;
  const supabase = createAdminClient();
  const { data, error } = await supabase.storage
    .from(BUCKET)
    .createSignedUploadUrl(path, { upsert: true });
  if (error) throw error;
  const { data: pub } = supabase.storage.from(BUCKET).getPublicUrl(path);
  return { token: data.token, path, publicUrl: pub.publicUrl };
}

/** Sobe bytes (de uma imagem gerada por IA, por exemplo) direto pro
 *  bucket via service role e devolve a URL pública. */
export async function uploadCarrosselFotoBytes(
  bytes: Buffer,
  contentType = "image/png",
): Promise<string> {
  const path = `__carrosseis/ai-${Date.now()}.png`;
  const supabase = createAdminClient();
  const { error } = await supabase.storage
    .from(BUCKET)
    .upload(path, bytes, { contentType, upsert: true });
  if (error) throw error;
  const { data: pub } = supabase.storage.from(BUCKET).getPublicUrl(path);
  return pub.publicUrl;
}
