# Padrões geométricos de fundo

Coloque aqui de 1 a 5 imagens PNG/SVG/JPG com os padrões geométricos
abstratos que aparecem como **fundo sutil** em todas as páginas
internas da revista (com baixa opacidade, ~6%).

## Nomes esperados

Os arquivos podem ter qualquer extensão (`.png`, `.jpg`, `.svg`,
`.webp`), mas o **stem** precisa ser:

- `pattern-1`
- `pattern-2`
- `pattern-3`
- `pattern-4`
- `pattern-5`

A engine carrega todos os arquivos `pattern-*` que encontrar e cicla
entre eles ao longo das páginas. Se houver só 2 patterns, alterna
1, 2, 1, 2, …. Se a pasta estiver vazia, nenhum fundo é aplicado.

## Recomendações

- Resolução: pelo menos 1500px no maior lado (vai escalar pra A4).
- Cores fortes funcionam bem porque são renderizadas com `opacity: 0.06`.
- Imagens com fundo transparente PNG ficam melhor sobre páginas claras.
- Para páginas escuras (capa, contracapa, hero de evento), o efeito
  vai ficar bem discreto — o que é desejável pra não competir com
  fotos full-bleed.
