"use client";

import { useState } from "react";
import { deleteLeafAsset } from "../asset-upload-action";

export interface GalleryItem {
  url: string;
  name: string;
  category: string;
}

/** Grid consolidado de todos os assets da marca, agrupado por categoria.
 *  Cada item tem miniatura + nome + Excluir (remove do bucket via server
 *  action e some do grid). */
export function GalleryGrid({ items }: { items: GalleryItem[] }) {
  const [list, setList] = useState(items);
  const [deleting, setDeleting] = useState<string | null>(null);

  async function del(item: GalleryItem) {
    if (
      !window.confirm(
        `Excluir "${item.name}"? Esta ação não pode ser desfeita.`,
      )
    ) {
      return;
    }
    setDeleting(item.url);
    const r = await deleteLeafAsset(item.url);
    setDeleting(null);
    if (r.ok) {
      setList((l) => l.filter((i) => i.url !== item.url));
    } else {
      window.alert(r.error);
    }
  }

  if (list.length === 0) {
    return (
      <p className="text-sm text-g60">
        Nenhum asset ainda. Use o botão <strong>Subir biblioteca</strong> ou{" "}
        <strong>Carregar ZIP</strong> nas categorias.
      </p>
    );
  }

  const categories = Array.from(new Set(list.map((i) => i.category)));

  return (
    <div className="space-y-10">
      {categories.map((cat) => {
        const catItems = list.filter((i) => i.category === cat);
        return (
          <section key={cat}>
            <h2 className="text-sm font-semibold text-onix-900 mb-3 flex items-center gap-2">
              {cat}
              <span className="text-[10px] font-medium text-onix-500 uppercase tracking-wider">
                {catItems.length} arquivo{catItems.length === 1 ? "" : "s"}
              </span>
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {catItems.map((it) => (
                <div
                  key={it.url}
                  className="flex flex-col gap-2 rounded-lg border border-onix-100 bg-white p-3"
                >
                  <div
                    className="aspect-square w-full rounded border border-onix-100 bg-onix-50 bg-center bg-no-repeat bg-contain"
                    style={{ backgroundImage: `url("${it.url}")` }}
                  />
                  <div
                    className="text-[10px] text-onix-700 truncate"
                    title={it.name}
                  >
                    {it.name}
                  </div>
                  <button
                    type="button"
                    onClick={() => void del(it)}
                    disabled={deleting === it.url}
                    className="text-[11px] font-medium text-rose-600 hover:underline disabled:opacity-50 self-start"
                  >
                    {deleting === it.url ? "Excluindo…" : "Excluir"}
                  </button>
                </div>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
