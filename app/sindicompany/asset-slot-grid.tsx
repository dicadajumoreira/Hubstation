"use client";

import { useEffect, useState } from "react";
import { ByAssetSlot } from "./by-assets-slot";

type UploadIntentFn = (
  slot: number,
  ext: string,
) => Promise<
  | { ok: true; uploadUrl: string; token: string; path: string; publicUrl: string }
  | { ok: false; error: string }
>;

const STORAGE_PREFIX = "sindicompany.extra-slots.";

interface AssetSlotGridProps {
  /** Chave única do grid pra persistir contador de "+ Novo slot" no
   *  localStorage. Ex: "consvicta.patterns". */
  storageKey: string;
  /** Slots ja preenchidos vindos do server (Supabase). Tamanho =
   *  baseline (= max(slots subidos, library_size, default)). */
  initialUrls: (string | null)[];
  /** Label do tipo de asset (Pattern/Icon/Logo/Fundo) — passa direto
   *  pro ByAssetSlot. */
  label: string;
  /** Prefixo opcional pra hint inline (ex: "Slide" → mostra
   *  "Slide 1", "Slide 2"). String pura — funcoes NAO sao
   *  serializaveis de Server pra Client Component no Next.js. */
  hintPrefix?: string;
  /** Aspect ratio do preview (default quadrado, "wide" pra logos). */
  aspect?: "square" | "wide";
  /** Server action que cria intent de upload (mesma assinatura do
   *  ByAssetSlot). */
  uploadIntent: UploadIntentFn;
  /** Classes do container do grid. */
  gridClassName?: string;
}

/** Grid wrapper client-side que: (1) renderiza slots iniciais vindos do
 *  Supabase, (2) adiciona slots ephemeros via "+ Novo slot" persistidos
 *  no localStorage. Cada slot extra fica vazio até user dropar um
 *  arquivo. */
export function AssetSlotGrid({
  storageKey,
  initialUrls,
  label,
  hintPrefix,
  aspect = "square",
  uploadIntent,
  gridClassName = "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4",
}: AssetSlotGridProps) {
  const fullKey = STORAGE_PREFIX + storageKey;
  const [extra, setExtra] = useState(0);

  useEffect(() => {
    try {
      const v = parseInt(localStorage.getItem(fullKey) || "0", 10);
      if (Number.isFinite(v) && v > 0) setExtra(v);
    } catch {
      // localStorage indisponivel (private mode) — extra fica 0
    }
  }, [fullKey]);

  const addSlot = () => {
    setExtra((v) => {
      const next = v + 1;
      try {
        localStorage.setItem(fullKey, String(next));
      } catch {
        // ignora
      }
      return next;
    });
  };

  const resetExtra = () => {
    setExtra(0);
    try {
      localStorage.removeItem(fullKey);
    } catch {
      // ignora
    }
  };

  const totalSlots = initialUrls.length + extra;
  const slots = Array.from({ length: totalSlots }, (_, i) => i + 1);

  return (
    <div>
      <div className={gridClassName}>
        {slots.map((slot) => (
          <ByAssetSlot
            key={slot}
            slot={slot}
            label={label}
            hint={hintPrefix ? `${hintPrefix} ${slot}` : undefined}
            initialUrl={initialUrls[slot - 1] ?? null}
            uploadIntent={uploadIntent}
            aspect={aspect}
          />
        ))}
        <button
          type="button"
          onClick={addSlot}
          aria-label="Adicionar novo slot"
          className="rounded border-2 border-dashed border-onix-200 bg-onix-50/40 flex flex-col items-center justify-center gap-1 p-3 aspect-square hover:border-mint-500 hover:bg-mint-50/40 transition cursor-pointer"
        >
          <span className="text-3xl font-light leading-none text-onix-700">
            +
          </span>
          <span className="text-[10px] text-g60 uppercase tracking-wider">
            Novo slot
          </span>
        </button>
      </div>
      {extra > 0 && (
        <button
          type="button"
          onClick={resetExtra}
          className="mt-2 text-[11px] text-rose-600 hover:underline"
        >
          Remover {extra} slot{extra > 1 ? "s" : ""} extra{extra > 1 ? "s" : ""}
        </button>
      )}
    </div>
  );
}
