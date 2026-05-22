"use client";

// Barra de exclusao em massa. Fica DENTRO do <form action={excluirVarios...}>
// que envolve a tabela. As linhas tem <input class="carrossel-check"
// name="ids" value={id}>; aqui controlamos o "selecionar todos" e o submit
// com confirmacao. Lê os checkboxes via DOM (sao server-rendered).
export function BulkDeleteBar() {
  function checks(): HTMLInputElement[] {
    return Array.from(
      document.querySelectorAll<HTMLInputElement>("input.carrossel-check"),
    );
  }

  function toggleAll(e: React.ChangeEvent<HTMLInputElement>) {
    const on = e.target.checked;
    for (const cb of checks()) cb.checked = on;
  }

  function onDelete(e: React.MouseEvent<HTMLButtonElement>) {
    const selecionados = checks().filter((cb) => cb.checked);
    if (selecionados.length === 0) {
      e.preventDefault();
      window.alert("Selecione ao menos um carrossel.");
      return;
    }
    if (
      !window.confirm(
        `Excluir ${selecionados.length} carrossel(éis)? Esta ação não pode ser desfeita.`,
      )
    ) {
      e.preventDefault();
    }
  }

  return (
    <div className="flex items-center justify-between gap-3 px-5 py-3 border-b border-onix-100 bg-onix-50/60">
      <label className="flex items-center gap-2 text-xs text-g60 cursor-pointer">
        <input
          type="checkbox"
          onChange={toggleAll}
          className="rounded border-onix-300"
        />
        Selecionar todos
      </label>
      <button
        type="submit"
        onClick={onDelete}
        className="inline-flex items-center px-3 py-1.5 rounded-md text-xs font-medium text-red-700 border border-red-200 hover:bg-red-50"
      >
        Excluir selecionados
      </button>
    </div>
  );
}
