"use client";

import { useEffect, useState } from "react";

const STORAGE_PREFIX = "sindicompany.extra-slots.";

/** Hook + botão "+ Novo slot" pra cada categoria de assets. Persiste
 *  contador no localStorage por chave (ex: 'consvicta.patterns' adiciona
 *  N slots além do baseline). Sem backend — refresh mantem porque vem
 *  do navegador. */
export function useExtraSlots(storageKey: string): {
  extra: number;
  addSlot: () => void;
  resetSlots: () => void;
} {
  const fullKey = STORAGE_PREFIX + storageKey;
  const [extra, setExtra] = useState(0);

  useEffect(() => {
    try {
      const v = parseInt(localStorage.getItem(fullKey) || "0", 10);
      if (Number.isFinite(v) && v > 0) setExtra(v);
    } catch {
      // localStorage indisponivel (private mode, etc) — comeca em 0
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

  const resetSlots = () => {
    setExtra(0);
    try {
      localStorage.removeItem(fullKey);
    } catch {
      // ignora
    }
  };

  return { extra, addSlot, resetSlots };
}

interface AddSlotButtonProps {
  storageKey: string;
  label?: string;
  className?: string;
}

/** Botão isolado que apenas adiciona +1 slot. Use com useExtraSlots
 *  em conjunto: o componente pai usa o hook pra ler o extra, este
 *  apenas modifica. */
export function AddSlotButton({
  storageKey,
  label = "+ Novo slot",
  className = "",
}: AddSlotButtonProps) {
  const { extra, addSlot, resetSlots } = useExtraSlots(storageKey);

  return (
    <div
      className={`rounded border-2 border-dashed border-onix-200 bg-onix-50/40 flex flex-col items-center justify-center gap-1.5 p-3 aspect-square hover:border-mint-400 hover:bg-mint-50/40 transition ${className}`}
    >
      <button
        type="button"
        onClick={addSlot}
        className="text-onix-700 hover:text-mint-700 text-3xl font-light leading-none"
        title="Adicionar mais 1 slot"
        aria-label={label}
      >
        +
      </button>
      <span className="text-[10px] text-g60 uppercase tracking-wider">
        Novo slot
      </span>
      {extra > 0 && (
        <button
          type="button"
          onClick={resetSlots}
          className="text-[9px] text-rose-600 hover:underline"
        >
          reset (+{extra})
        </button>
      )}
    </div>
  );
}
