"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  uploadEmbeddedConsvictaAssets,
  type UploadResult,
} from "./upload-library-action";

/** Botão "Subir biblioteca embutida" — chama a server action que faz o
 *  upload de tudo (2 logos + 20 ícones curados) pros buckets do Supabase
 *  usando o service_role já configurado no Netlify. Mostra resultado
 *  inline (uploaded / failed / lista de erros). */
export function UploadLibraryButton() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<UploadResult | null>(null);
  const [confirming, setConfirming] = useState(false);

  const run = () => {
    setResult(null);
    startTransition(async () => {
      const r = await uploadEmbeddedConsvictaAssets();
      setResult(r);
      setConfirming(false);
      // Refresh pra que os slots da página mostrem as imagens recém-enviadas
      router.refresh();
    });
  };

  return (
    <div className="rounded-lg border border-mint-300 bg-mint-50 p-4 sm:p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-onix-900 mb-1">
            Subir biblioteca embutida pros slots
          </h3>
          <p className="text-xs text-g60 sm:max-w-2xl">
            Em 1 clique sobe os 2 logotipos (wordmark + símbolo) +
            20 ícones curados pros slots Supabase abaixo.
            Idempotente — pode rodar várias vezes, vai apenas substituir.
          </p>
        </div>
        {!confirming ? (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            disabled={pending}
            className="w-full sm:w-auto shrink-0 rounded-md bg-onix-900 text-white px-4 py-3 sm:py-2 text-sm font-semibold hover:bg-onix-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Subir biblioteca
          </button>
        ) : (
          <div className="shrink-0 flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
            <button
              type="button"
              onClick={() => setConfirming(false)}
              disabled={pending}
              className="w-full sm:w-auto rounded-md border border-onix-200 px-3 py-3 sm:py-2 text-sm hover:bg-white"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={run}
              disabled={pending}
              className="w-full sm:w-auto rounded-md bg-mint-600 text-white px-4 py-3 sm:py-2 text-sm font-semibold hover:bg-mint-700 disabled:opacity-50"
            >
              {pending ? "Enviando…" : "Confirmar envio"}
            </button>
          </div>
        )}
      </div>

      {result && (
        <div className="mt-4 rounded-md bg-white border border-onix-100 px-4 py-3 text-sm">
          {result.ok ? (
            <p className="text-mint-800 font-medium">
              ✓ Concluído: {result.uploaded} arquivos enviados, 0 falhas.
            </p>
          ) : (
            <p className="text-rose-700 font-medium">
              ⚠ {result.uploaded} enviados, {result.failed} falhou.
            </p>
          )}
          {result.failed > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-rose-700 break-all">
              {result.details
                .filter((d) => !d.ok)
                .map((d) => (
                  <li key={d.path}>
                    <code>{d.path}</code> — {d.error}
                  </li>
                ))}
            </ul>
          )}
          {result.ok && (
            <p className="mt-1 text-xs text-g60">
              Os slots abaixo já mostram os arquivos recém-enviados.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
