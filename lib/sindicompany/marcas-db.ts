import { createAdminClient } from "@/lib/supabase/admin";

// Camada de acesso a `marcas` (Fase 1 do multi-marca). Substitui os mapas
// chumbados BRAND_PREFIX/ROUTE/LABEL/HANDLE e os SYSTEM_* keyed por slug.
// O slug e o identificador estavel da marca (usado no codigo e nos buckets).
export type MarcaSlug = string;

const TABLE = "marcas";

/** Um arquivo de fonte registrado (vira um @font-face no engine). */
export interface MarcaFontFace {
  family: string;
  /** Peso CSS: número (400, 700) ou range de fonte variável ("100 900"). */
  weight: number | string;
  style: "normal" | "italic";
  /** Nome do arquivo dentro de {bucketPrefix}fonts/ no bucket. */
  file: string;
}

/** Tipografia data-driven da marca. As fontes (faces) sao importadas via
 *  ZIP no cadastro; display/body/numeric sao os stacks CSS aplicados. */
export interface MarcaTipografia {
  display: string;
  body: string;
  numeric: string;
  faces: MarcaFontFace[];
}

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
  /** Cores da marca (chaves: onix, mint, sand, lavender, purple, white,
   *  gray_5 — mesmas que o template do engine usa). null = usa o tema base. */
  paleta: Record<string, string> | null;
  /** Fontes da marca. null = usa as fontes embutidas do engine. */
  tipografia: MarcaTipografia | null;
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
  paleta: Record<string, string> | null;
  tipografia: MarcaTipografia | null;
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
    paleta: r.paleta,
    tipografia: r.tipografia,
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

export interface MarcaInput {
  slug: string;
  nome: string;
  handle: string;
  nicho?: string | null;
  bucketPrefix: string;
  routeSlug: string;
  ativo?: boolean;
  ordem?: number;
  persona?: string | null;
  assinatura?: string | null;
  temasSugeridos?: string[] | null;
  paleta?: Record<string, string> | null;
  tipografia?: MarcaTipografia | null;
}

export async function createMarca(input: MarcaInput): Promise<Marca> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from(TABLE)
    .insert({
      slug: input.slug,
      nome: input.nome,
      handle: input.handle,
      nicho: input.nicho ?? null,
      bucket_prefix: input.bucketPrefix,
      route_slug: input.routeSlug,
      ativo: input.ativo ?? true,
      ordem: input.ordem ?? 0,
      persona: input.persona ?? null,
      assinatura: input.assinatura ?? null,
      temas_sugeridos: input.temasSugeridos ?? null,
      paleta: input.paleta ?? null,
      tipografia: input.tipografia ?? null,
    })
    .select()
    .single();
  if (error || !data) throw new Error(error?.message ?? "Falha ao criar marca.");
  return fromRow(data as MarcaRow);
}

// Atualiza por slug (identidade estavel). slug NAO muda: e a FK de
// carrosseis.brand e o prefixo dos buckets.
export async function updateMarca(
  slug: string,
  patch: Partial<Omit<MarcaInput, "slug">>,
): Promise<void> {
  const supabase = createAdminClient();
  const row: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (patch.nome !== undefined) row.nome = patch.nome;
  if (patch.handle !== undefined) row.handle = patch.handle;
  if (patch.nicho !== undefined) row.nicho = patch.nicho;
  if (patch.bucketPrefix !== undefined) row.bucket_prefix = patch.bucketPrefix;
  if (patch.routeSlug !== undefined) row.route_slug = patch.routeSlug;
  if (patch.ativo !== undefined) row.ativo = patch.ativo;
  if (patch.ordem !== undefined) row.ordem = patch.ordem;
  if (patch.persona !== undefined) row.persona = patch.persona;
  if (patch.assinatura !== undefined) row.assinatura = patch.assinatura;
  if (patch.temasSugeridos !== undefined) row.temas_sugeridos = patch.temasSugeridos;
  if (patch.paleta !== undefined) row.paleta = patch.paleta;
  if (patch.tipografia !== undefined) row.tipografia = patch.tipografia;
  const { error } = await supabase.from(TABLE).update(row).eq("slug", slug);
  if (error) throw new Error(error.message);
}
