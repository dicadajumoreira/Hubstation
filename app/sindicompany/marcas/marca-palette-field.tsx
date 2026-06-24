"use client";

import { useState } from "react";

const HEX = /^#[0-9a-fA-F]{6}$/;

/** Campo de cor com swatch + caixa de texto sincronizados. A caixa de texto
 *  (name=paleta_<key>) é a fonte que vai no form — permite colar o hex exato
 *  da marca, coisa que o seletor de cor sozinho não deixa fazer bem. */
export function ColorField({
  name,
  label,
  papel,
  defaultValue,
}: {
  name: string;
  label: string;
  papel: string;
  defaultValue: string;
}) {
  const [v, setV] = useState(defaultValue);
  const valid = HEX.test(v);
  return (
    <div className="space-y-1">
      <div className="text-xs font-medium text-onix-900">{label}</div>
      <div className="text-[11px] text-g60 leading-tight">{papel}</div>
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-label={`${label} (seletor)`}
          value={valid ? v : "#000000"}
          onChange={(e) => setV(e.target.value)}
          className="h-9 w-10 shrink-0 cursor-pointer rounded-md border border-onix-100 bg-white p-0.5"
        />
        <input
          type="text"
          name={name}
          value={v}
          onChange={(e) => setV(e.target.value)}
          placeholder="#RRGGBB"
          spellCheck={false}
          className={`w-full rounded-md border bg-white px-2 py-1.5 text-xs font-mono uppercase text-onix-900 focus:outline-none focus:ring-2 focus:ring-mint-300 ${
            valid || v === "" ? "border-onix-100" : "border-red-400"
          }`}
        />
      </div>
    </div>
  );
}
