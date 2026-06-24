import type { Config } from "tailwindcss";

/**
 * Paleta oficial Sindicompany — Brand Hub 2026-05-17
 *  - Navy (mint legacy key "onix")
 *  - Cyan (mint legacy key "mint")
 *  - Beige
 *  - Lavender
 *  - Purple
 *  - Paper (neutral warm)
 *
 * Mantemos as chaves "mint" e "onix" como aliases legacy pros componentes
 * que ja usam `bg-mint-700`, `text-onix-900`, etc — so trocamos os
 * valores HEX. Novas chaves (beige, lavender, purple, paper) sao
 * disponibilizadas pra extensoes futuras.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Cyan (#88C8D0) — Brand Hub novo. Legacy key "mint".
        mint: {
          DEFAULT: "#88C8D0",
          50: "#F2FAFB",
          100: "#E0F2F4",
          300: "#B0DCE2",
          500: "#88C8D0",
          600: "#5FB0BB",
          700: "#3F8A95",
          800: "#2E6A73",
        },
        // Navy (#182028) — Brand Hub novo. Legacy key "onix".
        onix: {
          DEFAULT: "#182028",
          50: "#F2F3F5",
          100: "#E0E2E6",
          200: "#C2C6CC",
          300: "#9CA3AB",
          500: "#4C5664",
          800: "#1F2832",
          900: "#182028",
        },
        // Beige (#E0B098)
        beige: {
          DEFAULT: "#E0B098",
          50: "#FBF6F2",
          100: "#F4E7DD",
          300: "#ECC9B5",
          500: "#E0B098",
          700: "#A47659",
        },
        // Lavender (#BFC0FF)
        lavender: {
          DEFAULT: "#BFC0FF",
          50: "#F4F4FF",
          100: "#E5E5FF",
          300: "#D2D2FF",
          500: "#BFC0FF",
          700: "#7C7EE0",
        },
        // Purple (#8890D0) — IA/profundidade
        purple: {
          DEFAULT: "#8890D0",
          50: "#F0F1FA",
          100: "#DEDFF1",
          300: "#B5B9E3",
          500: "#8890D0",
          700: "#5B62A3",
        },
        // Paper (#FAF7F2) — fundo padrao
        paper: {
          DEFAULT: "#FAF7F2",
          warm: "#F2EDE5",
          line: "#E5DDD2",
          muted: "#8A8E96",
        },
        // Gray auxiliary (manteve compat com componentes antigos).
        g60: "#8A8E96",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["Provicali", "var(--font-sans)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
