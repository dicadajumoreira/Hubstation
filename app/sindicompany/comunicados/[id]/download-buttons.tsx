"use client";

import { useState } from "react";
import { toPng } from "html-to-image";

export function DownloadButtons({ baseName }: { baseName: string }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function baixar(nodeId: string, suffix: string, pixelRatio: number) {
    const node = document.getElementById(nodeId);
    if (!node) {
      setErro("Não encontrei a arte na página. Recarregue e tente de novo.");
      return;
    }
    setBusy(suffix);
    setErro(null);
    try {
      // Dois passes ajudam a embutir imagens externas de forma confiável.
      await toPng(node, { cacheBust: true, pixelRatio });
      const dataUrl = await toPng(node, { cacheBust: true, pixelRatio, backgroundColor: "#FBFAF6" });
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `${baseName}-${suffix}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao gerar a imagem.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => baixar("comunicado-a4", "A4", 3)}
          disabled={busy !== null}
          className="inline-flex items-center px-4 py-2 rounded-lg bg-onix-900 text-white text-sm font-medium hover:bg-onix-800 disabled:opacity-50"
        >
          {busy === "A4" ? "Gerando…" : "Baixar A4 (PNG)"}
        </button>
        <button
          type="button"
          onClick={() => baixar("comunicado-celular", "story", 1.5)}
          disabled={busy !== null}
          className="inline-flex items-center px-4 py-2 rounded-lg bg-mint-600 text-white text-sm font-medium hover:bg-mint-700 disabled:opacity-50"
        >
          {busy === "story" ? "Gerando…" : "Baixar Celular / Story (PNG)"}
        </button>
      </div>
      {erro && <p className="text-xs text-rose-600">{erro}</p>}
      <p className="text-[11px] text-g60">
        Dica: se algum logo não aparecer no PNG, abra a imagem do logo direto no navegador uma vez (pra carregar) e gere de novo, ou use a captura de tela do preview abaixo.
      </p>
    </div>
  );
}
