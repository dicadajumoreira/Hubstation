"use client";

import { useState } from "react";
import { toPng } from "html-to-image";

interface PrintButtonProps {
  baseName?: string;
}

export function PrintButton({ baseName }: PrintButtonProps) {
  const [busy, setBusy] = useState<"pdf" | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [progresso, setProgresso] = useState<string | null>(null);

  async function baixarPdf() {
    const isMobile = typeof window !== "undefined" && window.matchMedia("(max-width: 900px)").matches;
    setBusy("pdf");
    setErro(null);
    setProgresso(null);
    try {
      const pages = Array.from(document.querySelectorAll<HTMLElement>(".bv-page"));
      if (pages.length === 0) {
        setErro("Páginas não encontradas.");
        setBusy(null);
        return;
      }
      // Em mobile pixelRatio 1 — A4 a 96dpi (794x1123 px) ~ 3.6 MP por
      // pagina, ja boa pra tela; pra impressao, gere do desktop.
      const pixelRatio = isMobile ? 1 : 2;
      const { jsPDF } = await import("jspdf");
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4", compress: true });

      for (let i = 0; i < pages.length; i++) {
        setProgresso(`Página ${i + 1} de ${pages.length}…`);
        let dataUrl: string;
        try {
          await toPng(pages[i], { cacheBust: true, pixelRatio });
          dataUrl = await toPng(pages[i], {
            cacheBust: true,
            pixelRatio,
            backgroundColor: "#FFFFFF",
          });
        } catch (e) {
          throw new Error(`Página ${i + 1}: ${e instanceof Error ? e.message : String(e)}`);
        }
        if (i > 0) pdf.addPage("a4", "portrait");
        pdf.addImage(dataUrl, "PNG", 0, 0, 210, 297, undefined, "FAST");
      }

      const file = (baseName?.trim() || "revista-boas-vindas")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "");
      const fileName = `${file || "revista-boas-vindas"}.pdf`;

      const blob = pdf.output("blob");
      const url = URL.createObjectURL(blob);

      // Tenta o download via <a download>. Funciona em desktop e em iOS
      // Safari 13+. Em iOS antigo o atributo download e ignorado e o
      // browser navega pro blob URL — tambem ok, mostra o PDF inline e
      // o usuario usa o "Compartilhar" do sistema.
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();

      // Fallback explicito pra iOS Safari, que as vezes nao reage ao
      // .click() programatico em <a download> e nem mostra o PDF nem
      // baixa. Se a aba continuar viva 600ms depois (sinal que nao
      // baixou nem navegou), forca a navegacao pro blob URL.
      if (isMobile) {
        setProgresso("Abrindo PDF…");
        setTimeout(() => {
          // Se a navegacao ja saiu, esse codigo nao executa.
          window.location.href = url;
        }, 600);
      } else {
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao gerar o PDF.");
    } finally {
      setBusy(null);
      setProgresso(null);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={baixarPdf}
        disabled={busy !== null}
        className="rounded-md bg-mint-600 hover:bg-mint-700 disabled:opacity-50 text-white text-sm font-medium px-4 py-1.5"
      >
        {busy === "pdf" ? (progresso ?? "Gerando PDF…") : "Baixar PDF"}
      </button>
      <button
        type="button"
        onClick={() => window.print()}
        disabled={busy !== null}
        className="rounded-md border border-white/30 text-white text-xs font-medium px-3 py-1.5 hover:bg-white/10 disabled:opacity-50"
      >
        Imprimir
      </button>
      {erro && <span className="text-xs text-rose-300 ml-2">{erro}</span>}
    </div>
  );
}
