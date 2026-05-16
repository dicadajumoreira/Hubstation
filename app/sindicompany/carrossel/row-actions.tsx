"use client";

import Link from "next/link";
import { useTransition } from "react";
import { excluirCarrosselAction } from "./actions";

export function CarrosselRowActions({
  id,
  titulo,
}: {
  id: string;
  titulo: string;
}) {
  const [pending, startTransition] = useTransition();

  function handleDelete() {
    const ok = window.confirm(
      `Excluir o carrossel "${titulo}"? Esta acao nao pode ser desfeita.`,
    );
    if (!ok) return;
    startTransition(async () => {
      await excluirCarrosselAction(id);
    });
  }

  return (
    <div className="flex items-center gap-2">
      <Link
        href={`/sindicompany/carrossel/${id}`}
        className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium text-onix-900 border border-onix-200 hover:bg-onix-50"
      >
        Abrir
      </Link>
      <button
        type="button"
        onClick={handleDelete}
        disabled={pending}
        className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium text-red-700 border border-red-200 hover:bg-red-50 disabled:opacity-50"
      >
        {pending ? "Excluindo…" : "Excluir"}
      </button>
    </div>
  );
}
