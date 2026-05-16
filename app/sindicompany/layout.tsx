import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sindicompany — Comunicação",
  description: "Plataforma de comunicação editorial da Sindicompany.",
};

// Fontes oficiais do site Sindicompany (Provicali + Epilogue), embutidas
// via @font-face. Os arquivos vivem em /public/fonts/ e são os mesmos
// usados na engine de geração de revista (consistência de marca).
const FONT_FACE_CSS = `
@font-face {
  font-family: 'Provicali';
  src: url('/fonts/Provicali.otf') format('opentype');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'Epilogue';
  src: url('/fonts/Epilogue-Variable.woff2') format('woff2-variations');
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'Epilogue';
  src: url('/fonts/Epilogue-VariableItalic.woff2') format('woff2-variations');
  font-weight: 100 900;
  font-style: italic;
  font-display: swap;
}

/* Aplica Epilogue como fonte padrão do painel; Provicali nos títulos. */
.sindicompany-shell {
  font-family: 'Epilogue', 'DejaVu Sans', 'Liberation Sans', system-ui, sans-serif;
}
.sindicompany-shell h1,
.sindicompany-shell h2,
.sindicompany-shell h3,
.sindicompany-shell h4 {
  font-family: 'Provicali', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
  letter-spacing: -0.01em;
}
`.trim();

export default function SindicompanyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="sindicompany-shell min-h-screen bg-onix-50 text-onix-900">
      <style dangerouslySetInnerHTML={{ __html: FONT_FACE_CSS }} />
      {children}
    </div>
  );
}
