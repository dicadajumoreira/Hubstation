import { createAdminClient } from "@/lib/supabase/admin";

// Camada de acesso a `marcas` (Fase 1 do multi-marca). Substitui os mapas
// chumbados BRAND_PREFIX/ROUTE/LABEL/HANDLE e os SYSTEM_* keyed por slug.
// O slug e o identificador estavel da marca (usado no codigo e nos buckets).
export type MarcaSlug = string;

const TABLE = "marcas";

export interface Marca {
  id: string;
  slug: string;
  nome: string;
  handle: string;
  nicho: string | null;
  /** Prefixo dos buckets de assets da marca: "__", "__by-", "__consvicta-". */
  bucketPrefix: string;
  /** Segmento da rota dos assets: "assets", "by-assets", ... (rota completa
   *  e /sindicompany/<routeSlug>). */
  routeSlug: string;
  ativo: boolean;
  ordem: number;
  /** System prompt da marca (voz, publico, proibicoes). */
  persona: string | null;
  /** Frase de fechamento da legenda. */
  assinatura: string | null;
  temasSugeridos: string[] | null;
}

interface MarcaRow {
  id: string;
  slug: string;
  nome: string;
  handle: string;
  nicho: string | null;
  bucket_prefix: string;
  route_slug: string;
  ativo: boolean;
  ordem: number;
  persona: string | null;
  assinatura: string | null;
  temas_sugeridos: string[] | null;
}

function fromRow(r: MarcaRow): Marca {
  return {
    id: r.id,
    slug: r.slug,
    nome: r.nome,
    handle: r.handle,
    nicho: r.nicho,
    bucketPrefix: r.bucket_prefix,
    routeSlug: r.route_slug,
    ativo: r.ativo,
    ordem: r.ordem,
    persona: r.persona,
    assinatura: r.assinatura,
    temasSugeridos: r.temas_sugeridos,
  };
}

export async function listMarcas(opts?: { ativo?: boolean }): Promise<Marca[]> {
  const supabase = createAdminClient();
  let q = supabase.from(TABLE).select("*").order("ordem", { ascending: true });
  if (opts?.ativo !== undefined) q = q.eq("ativo", opts.ativo);
  const { data, error } = await q;
  if (error || !data) return [];
  return (data as MarcaRow[]).map(fromRow);
}

export async function getMarca(slug: string): Promise<Marca | null> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .select("*")
    .eq("slug", slug)
    .maybeSingle();
  if (error || !data) return null;
  return fromRow(data as MarcaRow);
}
