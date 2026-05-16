"use client";

import { useState, useTransition } from "react";
import { regenerateCarrosselAction } from "../actions";

export function RegenerateButton({ id, label = "Gerar slides agora" }: { id: string; label?: string }) {
  const [pending, start] = useTransition();
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      disabled={pending}
      onClick={() => {
        start(async () => {
          await regenerateCarrosselAction(id);
          setDone(true);
        });
      }}
      className="rounded-lg bg-onix-900 text-white px-4 py-2 text-sm font-medium hover:bg-onix-800 disabled:opacity-50"
    >
      {pending ? "Disparando…" : done ? "✓ Disparado" : label}
    </button>
  );
}
