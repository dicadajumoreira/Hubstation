"use client";

import { useState } from "react";

export function LegendaCopy({ legenda }: { legenda: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="space-y-2">
      <pre className="whitespace-pre-wrap text-sm font-sans text-onix-900 bg-onix-50 rounded-lg px-4 py-3 max-h-72 overflow-auto">
        {legenda}
      </pre>
      <button
        type="button"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(legenda);
            setCopied(true);
            setTimeout(() => setCopied(false), 2500);
          } catch {
            // ignore — pode falhar em http (sem clipboard API)
          }
        }}
        className="text-xs font-medium text-mint-700 hover:text-mint-800 underline-offset-2 hover:underline"
      >
        {copied ? "✓ Copiado" : "Copiar legenda"}
      </button>
    </div>
  );
}
