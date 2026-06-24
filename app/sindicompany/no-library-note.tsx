/** Box informativo pra páginas de assets que NÃO têm biblioteca
 *  embutida (Sindicompany, By Sindicompany). Explica que o botão
 *  "Subir biblioteca" — disponível na página Consvicta — ainda não
 *  existe pra esta marca, e que assets desta marca devem ser
 *  uploadados manualmente nos slots abaixo. */
export function NoLibraryNote({ brand }: { brand: string }) {
  return (
    <div className="rounded-lg border border-onix-200 bg-onix-50/60 p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <span className="text-lg leading-none mt-0.5">📦</span>
        <div>
          <h3 className="text-sm font-semibold text-onix-900 mb-1">
            Biblioteca embutida não disponível pra {brand}
          </h3>
          <p className="text-xs text-g60">
            Sobe os assets manualmente nos slots abaixo. O botão{" "}
            <strong>Subir biblioteca</strong> está disponível só na página
            Consvicta porque é a única marca com biblioteca SVG embutida no
            código (patterns, fundos, logos extraídos do brand book). Pra ter o
            mesmo botão aqui, precisamos primeiro montar uma biblioteca pra
            {" "}{brand}.
          </p>
        </div>
      </div>
    </div>
  );
}
