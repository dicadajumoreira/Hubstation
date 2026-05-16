"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { copiarAssetsParaBy } from "../revista/nova/upload-actions";

export function CopiarAssetsButton() {
  const [pending, startTransition] = useTransition();
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const router = useRouter();

  function handleClick() {
    const ok = window.confirm(
      "Copiar TODOS os Patterns, Icons, Fundo Carrossel e Logotipos do " +
        "@sindicompanybr pra o @bysindicompany? Isso sobrescreve o que " +
        "ja existir nos buckets do By.",
    );
    if (!ok) return;
    setMsg("");
    setErr("");
    startTransition(async () => {
      const r = await copiarAssetsParaBy();
      if (r.ok) {
        setMsg(`Copiado: ${r.resumo}`);
        router.refresh();
      } else {
        setErr(r.error);
      }
    });
  }

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <button
        type="button"
        onClick={handleClick}
        disabled={pending}
        className="inline-flex items-center gap-1.5 rounded-lg border border-onix-200 bg-white hover:bg-onix-50 text-onix-900 text-sm font-medium px-3 py-2 disabled:opacity-50"
      >
        {pending ? "Copiando…" : "⇄ Copiar assets do @sindicompanybr"}
      </button>
      {msg && <span className="text-xs text-mint-700">{msg}</span>}
      {err && <span className="text-xs text-red-700">{err}</span>}
    </div>
  );
}
