"use client";

import { useEffect, useState } from "react";

export function CarrosselViewer({ slides }: { slides: string[] }) {
  const [idx, setIdx] = useState(0);
  const total = slides.length;

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowLeft") setIdx((i) => Math.max(0, i - 1));
      if (e.key === "ArrowRight") setIdx((i) => Math.min(total - 1, i + 1));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [total]);

  return (
    <div className="flex flex-col items-center gap-4 w-full max-w-md">
      <div
        className="w-full bg-onix-900 rounded-lg overflow-hidden ring-1 ring-white/10"
        style={{ aspectRatio: "4/5" }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={slides[idx]}
          alt={`Slide ${idx + 1}`}
          className="w-full h-full object-contain bg-onix-900"
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setIdx((i) => Math.max(0, i - 1))}
          disabled={idx === 0}
          className="rounded-md bg-white/10 hover:bg-white/20 px-3 py-1.5 text-sm disabled:opacity-30"
        >
          ← Anterior
        </button>
        <span className="text-sm font-medium tabular-nums w-16 text-center">
          {idx + 1} / {total}
        </span>
        <button
          type="button"
          onClick={() => setIdx((i) => Math.min(total - 1, i + 1))}
          disabled={idx === total - 1}
          className="rounded-md bg-white/10 hover:bg-white/20 px-3 py-1.5 text-sm disabled:opacity-30"
        >
          Próximo →
        </button>
      </div>

      <div className="flex gap-1.5 flex-wrap justify-center max-w-full">
        {slides.map((url, i) => (
          <button
            key={url}
            type="button"
            onClick={() => setIdx(i)}
            className={`w-2.5 h-2.5 rounded-full transition-colors ${i === idx ? "bg-mint-400" : "bg-white/30 hover:bg-white/50"}`}
            aria-label={`Slide ${i + 1}`}
          />
        ))}
      </div>

      <a
        href={slides[idx]}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-mint-400 hover:text-mint-300 underline underline-offset-2"
      >
        Abrir slide {idx + 1} em 4K (PNG)
      </a>
    </div>
  );
}
