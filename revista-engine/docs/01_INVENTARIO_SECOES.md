# Revista Engine — Inventário de Seções

> Documento-fundação da Fase 1 da engine genérica.
> Baseado na análise da skill `sindicompany-revista` e nas edições já produzidas (Gardens 04/2026, Club Park Butantã 04/2026, Villa Park Osasco).

---

## 1. Princípio arquitetural

A revista é composta por **seções modulares**, não por páginas fixas. Cada seção:

- Tem um **tipo** (que determina seu template)
- Recebe **dados estruturados** como entrada
- Sabe se renderizar em **A4** e em **Mobile** com paridade de conteúdo
- Declara à engine **quantas páginas ocupou** depois de renderizar
- Tem **regras próprias de paginação dinâmica** (mín/máx páginas em função do conteúdo)

A engine empilha as seções na ordem definida e calcula no final: numeração, sumário, `skip_pages`, e tamanho total da revista. **O número de páginas é resultado, não input.**

---

## 2. Categorização por origem do conteúdo

As 15 seções da revista se dividem em três categorias:

### A. Conteúdo editorial mensal compartilhado (mesma para todos os condomínios)

Produzido **uma vez por mês** pela equipe Sindicompany e reutilizado em todas as revistas daquele mês.

| Seção                   | Páginas típicas | Densidade variável? |
|-------------------------|-----------------|---------------------|
| Agenda Cultural         | 1               | Não                 |
| Matéria de Capa         | 2 (spread)      | Sim (até 4 págs)    |
| Dicas Práticas          | 1               | Sim (texto)         |
| Curiosidades do Setor   | 1               | Não                 |
| Novidades e Legislação  | 1               | Não                 |
| Receita do Mês          | 1               | Não                 |
| **Vida Condominial**    | **1–2**         | **Sim (texto)**     |
| Signos do Mês           | 1               | Não                 |

### B. Conteúdo específico do condomínio (variável por edição)

Preparado pela equipe do condomínio + síndico para cada edição.

| Seção                   | Páginas típicas | Densidade variável?              |
|-------------------------|-----------------|----------------------------------|
| Capa                    | 1               | Não                              |
| Carta do Síndico        | 1               | Não                              |
| Nosso Condomínio        | 2–8             | **Sim, muito** (por nº de fotos) |
| Nossos Números          | 1–2             | Sim (tabela de despesas)         |
| Advertências e Multas   | 1               | Sim (lista de assuntos)          |
| Expediente              | 1               | Não                              |

### C. Estrutural fixa (igual em todas)

Hardcoded no tema, sem necessidade de input.

| Seção        | Páginas | Notas                          |
|--------------|---------|--------------------------------|
| Contracapa   | 1       | Apenas tagline + redes sociais |

---

## 3. Catálogo completo das seções

### S01 — Capa

- **Tipo:** `cover`
- **Origem:** condomínio (fotos do condo) ou editorial mensal (Unsplash do tema)
- **Páginas:** 1 (sempre)
- **Inputs:**
  - `tema_materia` (string) — tema real da matéria de capa
  - `manchete` (string) — palavras-chave em destaque
  - `subtitulo` (string, máx 12 palavras)
  - `chamadas` (3 strings curtas) — chamadas no rodapé
  - `foto_capa` (path ou URL Unsplash) — fundo 100%
  - `edicao_label` (string) — "EDIÇÃO XX/AAAA · @sindicompanybr"
- **Regras:** foto cobre 100%, overlay gradient obrigatório, logo em mix-blend-mode screen.

---

### S02 — Carta do Síndico

- **Tipo:** `letter`
- **Origem:** condomínio
- **Páginas:** 1 (fixa)
- **Inputs:**
  - `genero` (`'masculino' | 'feminino'`) — define título
  - `nome_sindico` (string)
  - `cargo` (string, default `'Síndico(a) Profissional'`)
  - `foto_sindico` (path) — rosto 100% visível
  - `object_position` (string, default `'center 20%'`) — ajuste do enquadramento
  - `texto` (string, 350–450 palavras, 3 blocos)
- **Regras:** título adapta ao gênero ("Carta do Síndico" / "Carta da Síndica"). Foto é a única imagem permitida.

---

### S03 — Agenda Cultural

- **Tipo:** `cultural_agenda`
- **Origem:** editorial mensal
- **Páginas:** 1 (fixa)
- **Inputs:**
  - `hero` (objeto):
    - `categoria` (string) — "CINEMA", "SÉRIE", etc.
    - `titulo` (string)
    - `sinopse` (string)
    - `foto` (path/URL)
  - `cards_secundarios` (lista de 4–5 objetos):
    - `categoria`, `titulo`, `descricao_curta`
- **Regras:** zona A (hero ~50%) + zona B (grid 2 colunas).

---

### S04 — Matéria de Capa

- **Tipo:** `cover_story`
- **Origem:** editorial mensal
- **Páginas:** 2–4 (dinâmico — depende do conteúdo)
- **Inputs:**
  - `kicker` (string, máx 4 palavras)
  - `manchete` (string)
  - `subtitulo` (string)
  - `foto_principal` (path/URL)
  - `corpo_blocos` (lista de blocos): paragrafo, intertitulo, pull_quote, dado_box, foto_secundaria
  - `fontes` (lista de strings) — citação obrigatória
- **Regras:** citar fontes, sem traço longo, parágrafos máx 4 linhas. Pull quote 1 por spread.

---

### S05 — Dicas Práticas

- **Tipo:** `tips`
- **Origem:** editorial mensal
- **Páginas:** 1–2 (dinâmico — função do nº de dicas)
- **Inputs:**
  - `titulo_secao` (string)
  - `dicas` (lista de 6–8 objetos):
    - `numero` (auto), `titulo`, `corpo` (~1–2 linhas)
- **Regras:** tom direto, sem jargão, acionável.

---

### S06 — Curiosidades do Setor

- **Tipo:** `industry_facts`
- **Origem:** editorial mensal
- **Páginas:** 1 (fixa)
- **Inputs:**
  - `curiosidades` (lista de 4–5 objetos):
    - `fato` (string curta), `contexto`, `fonte` (SECOVI-SP, IBGE, CBIC, etc.)

---

### S07 — Novidades e Legislação

- **Tipo:** `news`
- **Origem:** editorial mensal
- **Páginas:** 1 (fixa)
- **Inputs:**
  - `noticias` (lista de 3 objetos):
    - `badge` (`'LEGISLAÇÃO' | 'MERCADO' | 'NOVIDADE' | 'TECNOLOGIA'`)
    - `titulo`, `data`, `resumo`, `fonte`
- **Regras:** notícias dos últimos 30 dias, fonte sempre citada.

---

### S08 — Nosso Condomínio (Manutenções)

- **Tipo:** `our_condo_maintenance`
- **Origem:** condomínio (FOTOS REAIS — nunca Unsplash)
- **Páginas:** **1–N (dinâmico)** — função do nº de pastas de manutenção
- **Inputs:**
  - `manutencoes` (lista de objetos):
    - `titulo` (= nome da subpasta no Drive)
    - `descricao` (do Doc/txt na subpasta)
    - `tipo_badge` (`'MANUTENÇÃO' | 'JARDIM' | 'ENGENHARIA' | 'OPERACIONAL'`)
    - `fotos` (lista de paths)
- **Regras de paginação dinâmica:**
  - Cada manutenção com **6+ fotos** → ganha página inteira de destaque (hero + grid)
  - Manutenções com **1–5 fotos** → vão para "páginas coletivas" (até 2 cards por página)
  - Padrão geral: máx 6 fotos por página em A4 (descoberto na edição abril 2026)
- **Badges visuais:**
  - `foto_jardim()` — pill mint com SVG de folha + "Revitalização de Jardim"
  - `foto_legenda()` — badge dark semi-transparente com texto branco

---

### S09 — Nosso Condomínio (Eventos)

- **Tipo:** `our_condo_events`
- **Origem:** condomínio
- **Páginas:** **1–N (dinâmico)**
- **Inputs:**
  - `mes_referencia` (string) — "O que aconteceu em [mês]"
  - `eventos` (lista de objetos):
    - `titulo`, `data`, `descricao`, `fotos` (lista de paths)
- **Regras:** máx 4 cards no grid (2×2). Foto sem legenda confirmada → exibir só foto. Nunca inventar legenda.

---

### S10 — Receita do Mês

- **Tipo:** `recipe`
- **Origem:** editorial mensal
- **Páginas:** 1 (fixa)
- **Inputs:**
  - `titulo_receita` (string)
  - `tempo_preparo` (string) — "25 min · serve 8 pessoas"
  - `foto_receita` (path/URL Unsplash)
  - `ingredientes` (lista de strings)
  - `modo_preparo` (lista de 4–6 strings)
  - `dica` (string opcional)
- **Regras:** receita simples, sazonal ao mês.

---

### S11 — Nossos Números

- **Tipo:** `our_numbers`
- **Origem:** condomínio
- **Páginas:** 1–2 (dinâmico, função da tabela de despesas)
- **Inputs:**
  - `mes_referencia` (string)
  - `kpis` (objeto): `receita`, `despesas`, `fundo_reserva`, `inadimplencia_pct`
  - `principais_despesas` (lista de objetos): `categoria`, `valor_brl`
  - `despesa_extra` (objeto opcional): `categoria`, `valor_brl`, `descricao`
  - `nota_transparencia` (string, default fixo)
- **Regras:** dados EXATOS do input, nunca inventar.

---

### S12 — Advertências e Multas

- **Tipo:** `warnings`
- **Origem:** condomínio
- **Páginas:** 1 (fixa)
- **Inputs:**
  - `total_advertencias` (int)
  - `total_multas` (int)
  - `valor_multas_brl` (float)
  - `infracoes_comuns` (lista de strings)
  - `assuntos_recorrentes` (lista de strings) — alimenta dicas "Como evitar"
- **Regras:** dados sempre agregados, nunca identificar moradores. Dicas "Como evitar" baseadas nos assuntos recorrentes específicos.

---

### S12B — Vida Condominial (matéria secundária)

- **Tipo:** `lifestyle_article`
- **Origem:** editorial mensal
- **Páginas:** 1–2 (dinâmico — função do tamanho do texto)
- **Inputs:**
  - `kicker` (string, máx 3 palavras)
  - `titulo` (string, 8–14 palavras)
  - `subtitulo` (string)
  - `corpo` (string, 300–600 palavras — uma das três estruturas: texto corrido, lista numerada, ou Q&A)
  - `foto_principal` (path/URL)
  - `fontes` (lista, opcional)
- **Regras:**
  - Tom MAIS LEVE que a Matéria de Capa (que é jornalística/embasada). Aqui é coloquial elegante, próximo, prático.
  - Tema muda a cada edição: pets, convivência, datas comemorativas do mês, comportamento, sazonalidade, sustentabilidade, saúde nas áreas comuns.
  - Pode usar listas curtas (3–6 itens) ou parágrafos curtos.
  - Posicionada após Advertências, antes de Signos — função editorial de "respiro" entre o normativo e o leve.
  - Fontes opcionais (ao contrário da Matéria de Capa, que exige).

---

### S13 — Signos do Mês

- **Tipo:** `horoscope`
- **Origem:** editorial mensal
- **Páginas:** 1 (fixa)
- **Inputs:**
  - `previsoes` (objeto com 12 chaves: `aries`, `touro`, ..., `peixes`):
    - cada uma: `texto` (~30–40 palavras)
- **Regras:** grid 3×4, tom leve.

---

### S14 — Expediente

- **Tipo:** `colophon`
- **Origem:** condomínio (parcial)
- **Páginas:** 1 (fixa)
- **Inputs:**
  - `nome_sindico` (vem da S02)
  - `nome_condominio` (vem do config)
  - `creditos_extras` (lista opcional)
- **Regras:** três créditos obrigatórios sempre presentes (Síndico, Equipe do Condomínio, Equipe Sindicompany).

---

### S15 — Contracapa

- **Tipo:** `back_cover`
- **Origem:** estrutural
- **Páginas:** 1 (fixa)
- **Inputs:**
  - `proxima_edicao_label` (string opcional)
- **Regras:** Onix + logo grande + tagline "Por mais lares." + handle.

---

## 4. Ordem default da revista

```
1.  S01  — Capa
2.  S02  — Carta do Síndico
3.  S03  — Agenda Cultural
4.  S04  — Matéria de Capa            (2–4 págs)
5.  S05  — Dicas Práticas
6.  S06  — Curiosidades do Setor
7.  S07  — Novidades e Legislação
8.  S08  — Nosso Condomínio (Manut.)  (1–N págs)
9.  S09  — Nosso Condomínio (Eventos) (1–N págs)
10. S10  — Receita do Mês
11. S11  — Nossos Números             (1–2 págs)
12. S12  — Advertências e Multas
13. S12B — Vida Condominial           (1–2 págs)   ← matéria secundária
14. S13  — Signos do Mês
15. S14  — Expediente
16. S15  — Contracapa
```

A ordem pode ser sobrescrita no `config.yaml` da edição se houver justificativa editorial.

---

## 5. Dimensões e formatos

| Formato     | CSS              | PDF efetivo   | Layout                          |
|-------------|------------------|---------------|---------------------------------|
| **A4**      | 794 × 1123 px    | A4 standard   | Multi-coluna, spreads possíveis |
| **Mobile**  | 540 × 960 px @2x | 1080 × 1920px | Single-column vertical          |

**Princípio de paridade:** todo conteúdo presente no A4 está presente no Mobile. Nada é cortado nem resumido. Mobile é uma revista premium nativa, não uma versão reduzida.

**Adaptações automáticas A4 → Mobile** (responsabilidade do template de cada seção):
- Colunas múltiplas viram lista vertical
- Spreads (S04 matéria, S08 manutenções com 6+ fotos) viram páginas separadas
- KPIs (S11) empilhados verticalmente
- Signos (S13) em 2 colunas × 6 linhas
- Tipografia escala: corpo mín 22–26px no mobile

---

## 6. Camada de tema (branding)

Tudo que é específico de marca fica num **objeto de tema** carregado pela engine, não hardcoded:

```yaml
# tema_sindicompany.yaml
identidade:
  nome: Sindicompany
  handle: "@sindicompanybr"
  tagline: "Por mais lares."

paleta:
  onix: "#1A1C29"
  sand: "#DABDA9"
  sand_90: "#EFCAAF"
  sand_80: "#D4AE94"
  mint: "#84C7D3"
  mint_80: "#76B1BC"
  lavender: "#B8C0FF"
  white: "#FFFFFF"
  gray_5: "#F4F4F5"
  gray_20: "#E0E0E2"

tipografia:
  titulos: Provicali
  corpo: Epilogue

assets_repo: "https://raw.githubusercontent.com/dicadajumoreira/Sindicompany/main/"
logos: { ... }
icons: { ... }
patterns: { ... }
```

Ter um `tema_generico.yaml` permite que **qualquer outra empresa** use a mesma engine — basta trocar tema, paleta e assets. Esse é o caminho para a engine ser de fato reutilizável fora da Sindicompany.

---

## 7. Mapa de dependências entre seções

Algumas seções compartilham dados — a engine resolve via referência, não duplicação:

```
config.condominio.nome    → S01, S04, S14, S15
config.edicao             → S01 (badge), S15 (próxima)
S02.nome_sindico          → S14 (créditos obrigatórios)
S02.genero                → S02 título, S14 cargo
S08.fotos                 → S01 capa (se compatível com tema da matéria)
S12.assuntos_recorrentes  → dicas "Como evitar" (mesma seção)
```

A engine valida essas dependências antes de renderizar — se faltar algo crítico, falha rápido com mensagem clara.

---

## 8. O que a engine precisa saber por seção

Para cada seção, a engine pergunta a si mesma:

1. **Quantas páginas precisa?** (`paginate(inputs) → int`)
2. **Como renderizar A4?** (`render_a4(inputs) → list[html_page]`)
3. **Como renderizar Mobile?** (`render_mobile(inputs) → list[html_page]`)
4. **Quais assets carregar?** (`required_assets(inputs) → list[url]`)
5. **Inputs estão válidos?** (`validate(inputs) → list[error]`)

Cada seção implementa essas 5 funções. A engine só orquestra.

---

## 9. Próximos documentos da Fase 1

- `02_INPUT_PACKAGE_SCHEMA.md` — estrutura padrão da pasta Drive
- `03_DRIVE_TO_INPUTS_MAPPING.md` — como Drive vira inputs estruturados
- `04_ENGINE_ARCHITECTURE.md` — arquitetura modular do código Python
- `05_EXAMPLE_GARDENS_05_2026.md` — exemplo concreto de pacote completo
