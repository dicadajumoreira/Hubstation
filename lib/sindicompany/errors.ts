/**
 * Helper compartilhado pra extrair uma mensagem legível de qualquer
 * erro — Error nativo, PostgrestError do Supabase, StorageError, etc.
 *
 * Sem isso, `String(e)` pode virar "[object Object]" e mensagens
 * úteis (`message`, `details`, `hint`) ficam escondidas.
 */
export function describeError(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  if (e && typeof e === "object") {
    const obj = e as Record<string, unknown>;
    const parts: string[] = [];
    if (typeof obj.message === "string" && obj.message) parts.push(obj.message);
    if (typeof obj.details === "string" && obj.details && obj.details !== obj.message) {
      parts.push(obj.details);
    }
    if (typeof obj.hint === "string" && obj.hint) parts.push(`(${obj.hint})`);
    if (parts.length > 0) return parts.join(" — ");
    try {
      return JSON.stringify(e);
    } catch {
      return "erro desconhecido";
    }
  }
  return "erro desconhecido";
}

/**
 * Tenta detectar erros típicos de migration faltando e retorna uma
 * mensagem que aponta pra solução, ou null se não bater no padrão.
 */
export function detectMigrationMissing(rawMessage: string): string | null {
  const m = rawMessage.toLowerCase();

  // Coluna inexistente: tenta achar o nome e indicar a migration certa.
  const colMatch =
    m.match(/column\s+["']?([a-z0-9_.]+)["']?\s+does not exist/) ||
    m.match(/could not find the\s+["']?([a-z0-9_]+)["']?\s+column/);
  if (colMatch) {
    const col = colMatch[1].split(".").pop()!;
    const mig = COLUMN_TO_MIGRATION[col];
    if (mig) {
      return `Coluna '${col}' não existe. Rode a migration ${mig} no SQL Editor do Supabase.`;
    }
    return `Coluna '${col}' não existe no banco. Verifique se rodou todas as migrations em supabase/migrations/.`;
  }

  if (m.includes("relation") && m.includes("does not exist")) {
    if (m.includes("condominios_meta")) {
      return "Tabela condominios_meta não existe. Rode a migration 20260509 no Supabase.";
    }
    if (m.includes("editoriais_mensais")) {
      return "Tabela editoriais_mensais não existe. Rode a migration 20260511 no Supabase.";
    }
    if (m.includes("carrosseis")) {
      return "Tabela carrosseis não existe. Rode a migration 20260520_carrosseis.sql no Supabase.";
    }
    if (m.includes("revistas")) {
      return "Tabela revistas não existe. Rode a migration 20260507 no Supabase.";
    }
    return "Uma tabela não existe ainda no banco. Rode as migrations pendentes em supabase/migrations/.";
  }

  if (m.includes("bucket not found") || m.includes("not found bucket")) {
    return "Bucket de storage não existe. Verifique as migrations 20260507 (revistas-pdfs), 20260509 (condominios-fotos) e 20260512 (editoriais-fotos).";
  }

  return null;
}

// Mapa coluna -> migration que cria. Mantém em sincronia com supabase/migrations/.
const COLUMN_TO_MIGRATION: Record<string, string> = {
  // 20260508
  sindico_nome: "20260508_revistas_form.sql",
  sindico_genero: "20260508_revistas_form.sql",
  tem_gestor: "20260508_revistas_form.sql",
  gestor_nome: "20260508_revistas_form.sql",
  drive_manutencao_url: "20260508_revistas_form.sql",
  drive_prestacao_url: "20260508_revistas_form.sql",
  tem_advertencias: "20260508_revistas_form.sql",
  multas_advertencias_obs: "20260508_revistas_form.sql",
  tem_eventos: "20260508_revistas_form.sql",
  drive_eventos_url: "20260508_revistas_form.sql",
  materia_capa_titulo: "20260508_revistas_form.sql",
  materia_capa_subtitulo: "20260508_revistas_form.sql",
  foto_capa_url: "20260508_revistas_form.sql",
  receita_sugerida: "20260508_revistas_form.sql",
  receita_titulo: "20260508_revistas_form.sql",
  notas_editor: "20260508_revistas_form.sql",
  // 20260510
  carta_sindico_tema: "20260510_revistas_cartas.sql",
  carta_sindico_texto: "20260510_revistas_cartas.sql",
  carta_gestor_tema: "20260510_revistas_cartas.sql",
  carta_gestor_texto: "20260510_revistas_cartas.sql",
  // 20260513
  logo_url: "20260513_logo_e_gestor_revista.sql",
  gestor_foto_url: "20260513_logo_e_gestor_revista.sql",
  // 20260514
  prestacao_arquivo_url: "20260514_prestacao_arquivo.sql",
  // 20260517
  manutencao_zip_url: "20260517_manutencao_zip.sql",
  // 20260518
  eventos_zip_url: "20260518_eventos_zip.sql",
  // 20260519
  manutencao_capa_url: "20260519_manutencao_capa.sql",
  // 20260521
  n_slides: "20260521_carrosseis_n_slides.sql",
};
