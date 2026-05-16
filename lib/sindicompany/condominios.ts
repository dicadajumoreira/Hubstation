/**
 * Lista canônica de condomínios sob gestão Sindicompany.
 *
 * Ordenado por nome. Mantenha ordem alfabética ao adicionar.
 *
 * Quando crescer e mudar com frequência, migrar para tabela Supabase
 * (public.condominios) e expor um endpoint pra editar via UI.
 */

export const CONDOMINIOS: readonly string[] = [
  "Alvorada",
  "Barra Viva Torre Alegria",
  "Baturité em Perdizes",
  "Blue Sky",
  "Cap d'Antibes",
  "Cinque Terre Residenza",
  "Ciudad Real",
  "Club Park Butantã",
  "Cond. Res. Maison du Rhone",
  "Condomíno Victoria",
  "Cores",
  "Elo & Elo Duo Caminhos da Lapa",
  "Fit Casa Rio Bonito",
  "Garden Living Club",
  "Giardino d' Itália",
  "GO! Barra Funda",
  "GO! Liberdade",
  "Highlights Jardim Prudência",
  "Hub Home Club Tatuapé",
  "I-Gloo",
  "Liberte",
  "Living for Consolação",
  "Monte Tabor",
  "Mundo Apto",
  "NYC Berrini",
  "Onze 22",
  "Organy",
  "Padre Carvalho",
  "Palm Beach",
  "Patricia",
  "Plano Estação Campo Limpo",
  "Plano Rio Bonito",
  "Platinum Building Berrini",
  "Port Saint Tropez",
  "Praça Saúde by You, Inc",
  "Res. Vita Parque Vila Formosa",
  "Reserva Verde",
  "Resid. Plano & Mooca - Praça Lion III",
  "Residencial Bela Vista",
  "Residencial Napoleão",
  "Serra da Mantiqueira",
  "Splendor Square",
  "Sublime",
  "Top Nine",
  "Upper Itaim",
  "Vera Cruz",
  "Vibra Butantã",
  "Villa Park Osasco",
  "Villa Sardenha",
  "Vista Verde",
  "Vivaz Vila Guilherme",
] as const;

export const CONDOMINIOS_SET = new Set<string>(CONDOMINIOS);

export function isCondominioValido(nome: string): boolean {
  return CONDOMINIOS_SET.has(nome);
}

/**
 * Slug URL-safe pra usar como [param] na rota /condominios/[slug].
 * Decodifica acento e troca não-alfanum por '-'.
 */
export function slugifyCondo(nome: string): string {
  return nome
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

const SLUG_TO_NOME = new Map<string, string>(
  CONDOMINIOS.map((nome) => [slugifyCondo(nome), nome]),
);

export function condoFromSlug(slug: string): string | null {
  return SLUG_TO_NOME.get(slug) ?? null;
}
