/**
 * DB helpers para o backoffice Sindicompany.
 *
 * Como o acesso é por senha única (não auth.users), todas as queries
 * usam o cliente admin (service_role). A camada Next.js valida a sessão
 * antes de chegar aqui.
 */

import { createAdminClient } from "@/lib/supabase/admin";

export type RevistaStatus = "em_producao" | "publicada" | "erro";
// 'empresa' = sindicatura feita por uma administradora/empresa — o
// texto da revista se dirige aos moradores como uma EQUIPE (1a pessoa
// do plural), nao como individuo.
export type Genero = "masculino" | "feminino" | "empresa";

export interface Revista {
  id: string;
  condominio: string;
  mes: number;
  ano: number;
  status: RevistaStatus;
  pdf_storage_path: string | null;
  paginas: number | null;
  gerado_em: string | null;
  erro_mensagem: string | null;
  // Liderança
  sindico_nome: string | null;
  sindico_genero: Genero | null;
  tem_gestor: boolean;
  gestor_nome: string | null;
  gestor_foto_url: string | null;
  gestor_titulo: string | null;
  is_by_sindico: boolean;
  foto_capa_clara: boolean;
  // Conteúdo do condomínio
  drive_manutencao_url: string | null;
  manutencao_zip_url: string | null;
  manutencao_capa_url: string | null;
  drive_prestacao_url: string | null;
  prestacao_arquivo_url: string | null;
  tem_advertencias: boolean;
  multas_advertencias_obs: string | null;
  tem_eventos: boolean;
  drive_eventos_url: string | null;
  eventos_zip_url: string | null;
  // Editorial
  materia_capa_titulo: string | null;
  materia_capa_subtitulo: string | null;
  foto_capa_url: string | null;
  receita_sugerida: string | null;
  receita_titulo: string | null;
  notas_editor: string | null;
  // Cartas
  carta_sindico_tema: string | null;
  carta_sindico_texto: string | null;
  carta_gestor_tema: string | null;
  carta_gestor_texto: string | null;
  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface RevistaInput {
  condominio: string;
  mes: number;
  ano: number;
  sindico_nome?: string;
  sindico_genero?: Genero;
  tem_gestor?: boolean;
  gestor_nome?: string;
  gestor_foto_url?: string;
  gestor_titulo?: string;
  is_by_sindico?: boolean;
  foto_capa_clara?: boolean;
  drive_manutencao_url?: string;
  manutencao_zip_url?: string;
  manutencao_capa_url?: string;
  prestacao_arquivo_url?: string;
  tem_advertencias?: boolean;
  multas_advertencias_obs?: string;
  tem_eventos?: boolean;
  drive_eventos_url?: string;
  eventos_zip_url?: string;
  materia_capa_titulo?: string;
  materia_capa_subtitulo?: string;
  foto_capa_url?: string;
  receita_titulo?: string;
  notas_editor?: string;
  carta_sindico_tema?: string;
  carta_sindico_texto?: string;
  carta_gestor_tema?: string;
  carta_gestor_texto?: string;
}

const TABLE = "revistas";
const BUCKET = "revistas-pdfs";

export async function listRevistas(): Promise<Revista[]> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .select("*")
    .order("ano", { ascending: false })
    .order("mes", { ascending: false })
    .order("created_at", { ascending: false });

  if (error) throw error;
  return (data ?? []) as Revista[];
}

export async function getRevista(id: string): Promise<Revista | null> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .select("*")
    .eq("id", id)
    .maybeSingle();

  if (error) throw error;
  return (data ?? null) as Revista | null;
}

export async function createRevista(input: RevistaInput): Promise<Revista> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .insert({
      ...input,
      status: "em_producao" as RevistaStatus,
    })
    .select()
    .single();

  if (error) throw error;
  return data as Revista;
}

export async function markRevistaPublished(
  id: string,
  pdf_storage_path: string,
  paginas: number,
): Promise<void> {
  const supabase = createAdminClient();
  const { error } = await supabase
    .from(TABLE)
    .update({
      status: "publicada" as RevistaStatus,
      pdf_storage_path,
      paginas,
      gerado_em: new Date().toISOString(),
      erro_mensagem: null,
    })
    .eq("id", id);

  if (error) throw error;
}

export async function deleteRevista(id: string): Promise<void> {
  const supabase = createAdminClient();

  // Apaga PDF do storage (se existir) antes de remover o registro.
  const revista = await getRevista(id);
  if (revista?.pdf_storage_path) {
    await supabase.storage.from(BUCKET).remove([revista.pdf_storage_path]);
  }

  const { error } = await supabase.from(TABLE).delete().eq("id", id);
  if (error) throw error;
}

export async function markRevistaErro(id: string, mensagem: string): Promise<void> {
  const supabase = createAdminClient();
  const { error } = await supabase
    .from(TABLE)
    .update({
      status: "erro" as RevistaStatus,
      erro_mensagem: mensagem,
    })
    .eq("id", id);

  if (error) throw error;
}

/** Upload do PDF gerado para o bucket; retorna o storage path. */
export async function uploadRevistaPdf(
  revistaId: string,
  pdfBytes: Buffer,
): Promise<string> {
  const path = `${revistaId}.pdf`;
  const supabase = createAdminClient();
  const { error } = await supabase.storage
    .from(BUCKET)
    .upload(path, pdfBytes, {
      contentType: "application/pdf",
      upsert: true,
    });

  if (error) throw error;
  return path;
}

/** Gera URL assinada (1h) para o PDF de uma revista. */
export async function getSignedPdfUrl(
  storagePath: string,
  expiresInSeconds = 3600,
): Promise<string> {
  const supabase = createAdminClient();
  const { data, error } = await supabase.storage
    .from(BUCKET)
    .createSignedUrl(storagePath, expiresInSeconds);

  if (error) throw error;
  return data.signedUrl;
}

export function formatEdicao(mes: number, ano: number): string {
  return `${String(mes).padStart(2, "0")} / ${ano}`;
}
