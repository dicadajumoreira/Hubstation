// Sindicompany Brand Hub library manifest.
// Espelha o padrão do Consvicta (consvicta-assets/library-manifest.ts).
// Arquivos físicos em `public/sindicompany-library/{logos,patterns,icons}/`.
//
// Brand Hub novo (paleta Navy/Cyan/Beige/Lavender/Purple/White, 2026-05-17):
// - Logos: 3 PNG masks paramétricas (símbolo recolorível via mask-image)
//   + variações horizontais pintadas. Mais variações podem ser adicionadas
//   conforme upload manual via /sindicompany/assets/brand-assets/logos.
// - Patterns: 5 cantos coloridos (1 por cor principal) — sobem em curadoria
//   no upload action quando os PNGs estiverem disponíveis em public/.
// - Icons: stroke 1.5 paramétrico via símbolo recolorível.

export const SINDICOMPANY_LIBRARY_LOGOS: ReadonlyArray<string> = [
  "sindicompany-horizontal-color.png",
  "sindicompany-horizontal-white.png",
  "sindicompany-horizontal-cyan.png",
  "sindicompany-horizontal-lavender.png",
  "sindicompany-horizontal-dark.png",
  "mask-houses.png",
  "mask-dot.png",
  "mask-outer-filled.png",
  "sindicompany-horizontal-color-2.png",
  "sindicompany-horizontal-color-alt.png",
];

export const SINDICOMPANY_LIBRARY_ICONS: ReadonlyArray<string> = [
  "icon-cyan-beige.png",
  "icon-beige-lavender.png",
  "icon-dark.png",
  "icon-white.png",
  "icon-cyan-photo.png",
  "icon-beige-photo.png",
];

export const SINDICOMPANY_LIBRARY_PATTERNS: ReadonlyArray<string> = [
  "canto-navy.png",
  "canto-cyan.png",
  "canto-beige.png",
  "canto-lavender.png",
  "canto-purple.png",
  "criativo-direito-navy.png",
  "criativo-direito-beige.png",
  "criativo-direito-purple.png",
  "criativo-esquerdo-navy.png",
  "decorativo-navy-2.png",
  "decorativo-beige-2.png",
  "decorativo-purple-2.png",
  "fundo-circ-navy.png",
  "fundo-circ-cyan.png",
  "fundo-circ-beige.png",
  "fundo-geo-navy.png",
  "fundo-geo-beige.png",
];
