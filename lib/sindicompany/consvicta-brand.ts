/**
 * Brand Book Consvicta — fonte unica de verdade pra cores e tipografia
 * da marca @consvictabr. Use estas constantes em qualquer arte/template
 * front-end que renderize material da Consvicta (carrosseis, comunicados,
 * revistas, etc).
 *
 * Posicionamento: Gestao Condominial Boutique. SP & RJ. Desde 2019.
 * Tagline oficial: "Administracao condominial que entrega resultado."
 * Manifesto: "Gestao condominial Boutique. Nao somos uma plataforma de
 *            gestao. Somos uma equipe especializada que conhece o seu
 *            condominio de perto."
 */

export const CONSVICTA_COLORS = {
  // Cor signature (Tiffany / Pantone 1837 Blue)
  tiffany: "#81D8D0",
  // Famila ouro — usar como secundaria/destaque
  ouroEnvelhecido: "#B08D57",
  ouroClaro: "#C9A96E",
  ouroEscuro: "#8A6A38",
  // Pretos e cinzas
  pretoProfundo: "#0A0A0A",
  grafiteEscuro: "#2B2B2B",
  cinzaMedio: "#6E6E6E",
  // Famila branco / off-white
  offWhite: "#F5F5F2",
  cream: "#F7F4EF",
  paper: "#FDFCF9",
  brancoPuro: "#FFFFFF",
} as const;

export const CONSVICTA_FONTS = {
  display: "'Cormorant Garamond', 'Liberation Serif', Georgia, serif",
  body: "'Outfit', 'Inter', system-ui, sans-serif",
  accentNumeric: "'Bebas Neue', 'Impact', sans-serif",
} as const;

/** URL p/ embutir as 3 famílias via Google Fonts em um <link href=...>. */
export const CONSVICTA_FONTS_GOOGLE_URL =
  "https://fonts.googleapis.com/css2?" +
  "family=Cormorant+Garamond:wght@400;500;600;700&" +
  "family=Outfit:wght@200;300;400;500;600&" +
  "family=Bebas+Neue&display=swap";

export const CONSVICTA_BRAND = {
  handle: "@consvictabr",
  tagline: "Administração condominial que entrega resultado.",
  posicionamento: "Gestão Condominial Boutique · SP & RJ · Desde 2019",
} as const;
