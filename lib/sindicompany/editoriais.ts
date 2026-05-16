/**
 * Editorial mensal — decisões compartilhadas entre todos os
 * condomínios pra uma dada edição (mes/ano):
 *   - matéria de capa (título + subtítulo + foto)
 *   - receita do mês
 *   - temas sugeridos das cartas do síndico e do gestor
 *   - notas pro editor (gerais)
 *
 * O texto da carta de cada síndico/gestor continua no registro
 * da revista (lib/sindicompany/db.ts), porque é específico de
 * cada condomínio.
 */

import { createAdminClient } from "@/lib/supabase/admin";

const TABLE = "editoriais_mensais";
const BUCKET = "editoriais-fotos";

export interface Editorial {
  mes: number;
  ano: number;
  materia_capa_titulo: string | null;
  materia_capa_subtitulo: string | null;
  foto_capa_url: string | null;
  receita_titulo: string | null;
  receita_descricao: string | null;
  carta_sindico_tema: string | null;
  carta_gestor_tema: string | null;
  notas_editor_geral: string | null;
  created_at: string;
  updated_at: string;
}

export interface EditorialInput {
  mes: number;
  ano: number;
  materia_capa_titulo?: string;
  materia_capa_subtitulo?: string;
  foto_capa_url?: string;
  receita_titulo?: string;
  receita_descricao?: string;
  carta_sindico_tema?: string;
  carta_gestor_tema?: string;
  notas_editor_geral?: string;
}

export async function getEditorial(mes: number, ano: number): Promise<Editorial | null> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .select("*")
    .eq("mes", mes)
    .eq("ano", ano)
    .maybeSingle();
  if (error) throw error;
  return (data ?? null) as Editorial | null;
}

export async function listEditoriais(): Promise<Editorial[]> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .select("*")
    .order("ano", { ascending: false })
    .order("mes", { ascending: false });
  if (error) throw error;
  return (data ?? []) as Editorial[];
}

export async function upsertEditorial(input: EditorialInput): Promise<Editorial> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .upsert(
      {
        mes: input.mes,
        ano: input.ano,
        materia_capa_titulo: input.materia_capa_titulo ?? null,
        materia_capa_subtitulo: input.materia_capa_subtitulo ?? null,
        foto_capa_url: input.foto_capa_url ?? null,
        receita_titulo: input.receita_titulo ?? null,
        receita_descricao: input.receita_descricao ?? null,
        carta_sindico_tema: input.carta_sindico_tema ?? null,
        carta_gestor_tema: input.carta_gestor_tema ?? null,
        notas_editor_geral: input.notas_editor_geral ?? null,
      },
      { onConflict: "mes,ano" },
    )
    .select()
    .single();
  if (error) throw error;
  return data as Editorial;
}

/** "Editorial está pronto pra gerar revista?" — campos mínimos preenchidos. */
export function editorialEstaPronto(e: Editorial | null): boolean {
  if (!e) return false;
  return Boolean(e.materia_capa_titulo && e.receita_titulo);
}

/** Sobe foto de capa pro bucket público e retorna a URL pública. */
export async function uploadEditorialFotoCapa(
  mes: number,
  ano: number,
  bytes: Buffer,
  contentType: string,
  ext: string,
): Promise<string> {
  const path = `${ano}-${String(mes).padStart(2, "0")}-${Date.now()}.${ext}`;
  const supabase = createAdminClient();
  const { error } = await supabase.storage
    .from(BUCKET)
    .upload(path, bytes, { contentType, upsert: true });
  if (error) throw error;
  const { data } = supabase.storage.from(BUCKET).getPublicUrl(path);
  return data.publicUrl;
}

export function formatMesAno(mes: number, ano: number): string {
  return `${String(mes).padStart(2, "0")}-${ano}`;
}

export function parseMesAno(slug: string): { mes: number; ano: number } | null {
  // formato: "MM-YYYY"
  const m = /^(\d{2})-(\d{4})$/.exec(slug);
  if (!m) return null;
  const mes = Number(m[1]);
  const ano = Number(m[2]);
  if (!Number.isInteger(mes) || mes < 1 || mes > 12) return null;
  if (!Number.isInteger(ano) || ano < 2025 || ano > 2030) return null;
  return { mes, ano };
}
