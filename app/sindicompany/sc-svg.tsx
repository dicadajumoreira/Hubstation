/**
 * SC_SVG — Componentes da marca Sindicompany (Brand Hub 2026-05-17).
 *
 * Símbolo paramétrico recolorível em runtime via CSS `mask-image` em
 * cima dos 3 PNGs alpha em /sindicompany-library/logos/ (mask-houses,
 * mask-dot, mask-outer-filled). Mesma técnica do Brand Hub original
 * (data.js + svg-kit.jsx) portada pra React.
 *
 * Cores oficiais (do Brand Hub):
 *   navy     #182028
 *   cyan     #88C8D0
 *   beige    #E0B098
 *   lavender #BFC0FF
 *   purple   #8890D0
 *   white    #FFFFFF
 *
 * Uso:
 *   <SCSymbol outer="#182028" dot="#E0B098" size={120} />
 *   <SCLogoHorizontal houseColor="#182028" dotColor="#E0B098" wordmarkColor="#182028" width={300} />
 */

import type { CSSProperties } from "react";

const MASK_HOUSES = "/sindicompany-library/logos/mask-houses.png";
const MASK_DOT = "/sindicompany-library/logos/mask-dot.png";
const MASK_OUTER = "/sindicompany-library/logos/mask-outer-filled.png";

interface SCSymbolProps {
  /** Cor das 4 casinhas (default Navy). */
  outer?: string;
  /** Cor da bolinha decorativa (default Beige). */
  dot?: string;
  /** Tamanho do símbolo em px (default 120). Mantém aspect 454:512. */
  size?: number;
  /** Cor única — quando definida, sobrescreve outer+dot (modo mono). */
  monoColor?: string;
  className?: string;
}

/** Símbolo Sindicompany paramétrico (casinhas + bolinha). */
export function SCSymbol({
  outer = "#182028",
  dot = "#E0B098",
  size = 120,
  monoColor,
  className,
}: SCSymbolProps) {
  const w = size;
  const h = Math.round((size * 512) / 454);
  const houseColor = monoColor ?? outer;
  const dotColor = monoColor ?? dot;
  return (
    <div
      className={className}
      style={{ position: "relative", width: w, height: h, display: "inline-block" }}
      aria-label="Sindicompany"
      role="img"
    >
      <div style={maskLayer(MASK_HOUSES, houseColor)} />
      <div style={maskLayer(MASK_DOT, dotColor)} />
    </div>
  );
}

interface SCLogoHorizontalProps {
  /** Cor das casinhas (default Navy). */
  houseColor?: string;
  /** Cor da bolinha (default Beige). */
  dotColor?: string;
  /** Cor do wordmark Provicali (default Navy). */
  wordmarkColor?: string;
  /** Largura total em px (default 300). */
  width?: number;
  /** Mono override (sobrescreve house+dot+wordmark). */
  monoColor?: string;
  className?: string;
}

/**
 * Logo horizontal Sindicompany = símbolo + wordmark "sindicompany" em
 * Provicali. Proporções extraídas do Brand Hub original:
 *  - largura símbolo: 18.3% do total
 *  - gap símbolo↔wordmark: 0.5% (quase zero)
 *  - wordmark height ≈ 51% da altura do símbolo
 */
export function SCLogoHorizontal({
  houseColor = "#182028",
  dotColor = "#E0B098",
  wordmarkColor = "#182028",
  width = 300,
  monoColor,
  className,
}: SCLogoHorizontalProps) {
  const symbolW = width * 0.183;
  const symbolH = symbolW * (512 / 454);
  const wordmarkH = symbolH * 0.51;
  const gap = width * 0.005;
  const hc = monoColor ?? houseColor;
  const dc = monoColor ?? dotColor;
  const wc = monoColor ?? wordmarkColor;
  return (
    <div
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap,
        width,
      }}
      aria-label="Sindicompany"
      role="img"
    >
      <SCSymbol outer={hc} dot={dc} size={symbolW} />
      <span
        style={{
          fontFamily: "Provicali, system-ui, sans-serif",
          fontSize: wordmarkH,
          lineHeight: 1,
          letterSpacing: "-0.02em",
          color: wc,
        }}
      >
        sindicompany
        <sup
          style={{
            fontFamily: "Epilogue, system-ui, sans-serif",
            fontSize: "0.18em",
            verticalAlign: "super",
            marginLeft: "0.05em",
          }}
        >
          ®
        </sup>
      </span>
    </div>
  );
}

interface SCSymbolWindowProps {
  /** URL da foto que preenche as casinhas. */
  photoSrc: string;
  /** Focal point CSS (default "center"). */
  photoFocus?: string;
  /** Cor da bolinha (default Beige). */
  dotColor?: string;
  size?: number;
  className?: string;
}

/** Variante onde uma foto preenche o recorte das casinhas (mask-image
 *  com cor → mask-image com background-image). */
export function SCSymbolWindow({
  photoSrc,
  photoFocus = "center",
  dotColor = "#E0B098",
  size = 200,
  className,
}: SCSymbolWindowProps) {
  const w = size;
  const h = Math.round((size * 512) / 454);
  return (
    <div
      className={className}
      style={{ position: "relative", width: w, height: h, display: "inline-block" }}
      aria-label="Sindicompany"
      role="img"
    >
      <div
        style={{
          ...absFill,
          WebkitMaskImage: `url(${MASK_HOUSES})`,
          maskImage: `url(${MASK_HOUSES})`,
          WebkitMaskRepeat: "no-repeat",
          maskRepeat: "no-repeat",
          WebkitMaskSize: "contain",
          maskSize: "contain",
          backgroundImage: `url(${photoSrc})`,
          backgroundSize: "cover",
          backgroundPosition: photoFocus,
        }}
      />
      <div style={maskLayer(MASK_DOT, dotColor)} />
    </div>
  );
}

const absFill: CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
};

function maskLayer(maskUrl: string, color: string): CSSProperties {
  return {
    ...absFill,
    WebkitMaskImage: `url(${maskUrl})`,
    maskImage: `url(${maskUrl})`,
    WebkitMaskRepeat: "no-repeat",
    maskRepeat: "no-repeat",
    WebkitMaskSize: "contain",
    maskSize: "contain",
    backgroundColor: color,
  };
}

/** Paleta oficial pra reuso em props. */
export const SC_PALETTE = {
  navy: "#182028",
  cyan: "#88C8D0",
  beige: "#E0B098",
  lavender: "#BFC0FF",
  purple: "#8890D0",
  white: "#FFFFFF",
  paper: "#FAF7F2",
  paperWarm: "#F2EDE5",
  line: "#E5DDD2",
  muted: "#8A8E96",
} as const;
