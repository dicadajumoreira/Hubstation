"use client";

import { useTransition } from "react";
import { excluirRevistaAction } from "./actions";

interface DeleteButtonProps {
  id: string;
  label: string; // "Janeiro / 2026 — Alvorada", pra confirm
}

export function DeleteRevistaButton({ id, label }: DeleteButtonProps) {
  const [isPending, startTransition] = useTransition();

  function onClick() {
    if (!confirm(`Excluir a revista de ${label}? Essa ação não pode ser desfeita.`)) {
      return;
    }
    const fd = new FormData();
    fd.set("id", id);
    startTransition(() => {
      excluirRevistaAction(fd);
    });
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isPending}
      className="text-xs text-red-700 hover:text-red-900 hover:underline disabled:opacity-50"
    >
      {isPending ? "Excluindo…" : "Excluir"}
    </button>
  );
}
