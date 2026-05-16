# Revista Engine — Sistema de Geração de Revistas Condominiais

> **Fase 1 em curso:** engine standalone, multi-condomínio, multi-empresa, lendo de Google Drive.
> **Versão da spec:** 2 (alinhada à estrutura real do Drive da Sindicompany).

---

## Por que existe

Hoje cada edição da revista mensal é produzida de forma artesanal: a Juliana conversa com Claude, manda fotos, faz revisões iterativas, ajusta páginas hardcoded. Funciona, mas não escala bem para vários condomínios e força a Juliana a estar presente em toda edição.

A Revista Engine resolve isso transformando o conhecimento editorial acumulado nas skills `sindicompany-revista` em uma **engine genérica** que:

1. Lê pacotes de inputs estruturados do Google Drive
2. Renderiza qualquer condomínio, qualquer empresa
3. Calcula páginas dinamicamente em função do conteúdo
4. Produz dois PDFs (A4 + Mobile) com paridade total
5. Deixa a equipe operar sem precisar do Claude para cada edição

---

## Decisões fundamentais (já tomadas)

| Tema                     | Decisão                                                                      |
|--------------------------|------------------------------------------------------------------------------|
| **Fonte dos inputs**     | Google Drive com estrutura `Mês > Condomínio > _Editorial Mensal`            |
| **Quem opera**           | Equipe Sindicompany (sem precisar Claude direto)                             |
| **Páginas**              | 100% dinâmicas — engine calcula em função do conteúdo                        |
| **Generalidade**         | Engine genérica, tema/branding em arquivo separado                           |
| **Conteúdo dual**        | Pacote editorial mensal compartilhado + pacote do condomínio específico      |
| **Formatos**             | A4 (794×1123 CSS) + Mobile (540×960 CSS @2x = 1080×1920 efetivo)             |
| **Paridade**             | Mobile carrega 100% do conteúdo do A4, layout próprio                        |
| **Convenções de input**  | Engine aceita 2: subpastas (Villa Park) **e** plana (Gardens)                |
| **Inferência de badges** | Automática por palavras-chave no nome — sem prefixos forçados                |
| **Config**               | Google Sheets com abas (não YAML)                                            |
| **Pré-revisão**          | Skill Humanizer + revisão pt-BR rodam automaticamente nos textos             |
| **Migração**             | Sem big-bang — edições antigas ficam, novas adotam padrão final gradualmente |

---

## Documentos da especificação

| Doc | Arquivo                          | O que contém                                            |
|-----|----------------------------------|---------------------------------------------------------|
| 00  | `00_HANDOFF.md`                  | Documento mestre de transferência (Drive IDs, contexto) |
| 01  | `01_INVENTARIO_SECOES.md`        | Catálogo das 16 seções, regras de paginação, inputs     |
| 02  | `02_INPUT_PACKAGE_SCHEMA.md`     | Estrutura padrão das pastas no Drive                    |
| 03  | `03_MIGRACAO_E_ADOCAO.md`        | Estratégia de migração gradual sem traumatizar a equipe |
| 04  | `04_ARQUITETURA_CODIGO.md`       | Arquitetura do código Python + classes principais       |

---

## Arquitetura em 3 camadas

```
┌──────────────────────────────────────────────────────────────────┐
│  CAMADA 3 — Cliente (Claude / Web futuro / CLI)                  │
│  "Gere a revista 05/2026 do Gardens"                             │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  CAMADA 2 — Engine (Python)                                      │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ Drive       │→ │ Validator   │→ │ Section Renderers (×15)  │  │
│  │ Loader      │  │ + Schema    │  │ ↓                        │  │
│  │ (Flat       │  └─────────────┘  │ Page Compositor          │  │
│  │  + SubFold) │                   │ ↓                        │  │
│  └─────────────┘                   │ Pre-revisão (Humanizer)  │  │
│         │                          │ ↓                        │  │
│         └──── tema.yaml ──────────→│ Playwright PDF generator │  │
│                                    └──────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  CAMADA 1 — Storage (Google Drive)                               │
│                                                                  │
│  📁 Revistas/                                                    │
│     ├── 📁 04 - 2026/                                            │
│     │   ├── 📁 _Editorial Mensal/                                │
│     │   ├── 📁 Gardens Living/                                   │
│     │   ├── 📁 Villa Park Osasco/                                │
│     │   └── ...                                                  │
│     └── 📁 Revistas Antigas/                                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Princípios de implementação

1. **Seções modulares.** Cada uma das 15 seções é uma classe Python com 5 métodos: `validate()`, `paginate()`, `required_assets()`, `render_a4()`, `render_mobile()`. A engine só orquestra.

2. **Páginas como resultado.** Nenhuma seção declara "quero ser página 8". Ela diz "preciso de N páginas" e a engine calcula numeração no fechamento.

3. **Tema desacoplado.** Cores, fontes, paleta, logos, assets ficam num `tema.yaml` separado. A engine não sabe nada sobre Sindicompany — só lê o tema atual.

4. **Validação cedo, mensagem humana.** Se faltar foto ou texto crítico, a engine para imediatamente com mensagem em português dizendo exatamente o que falta e onde corrigir no Drive.

5. **Paralelismo agressivo.** Downloads, conversões, renderizações por seção, tudo em ThreadPoolExecutor. Meta: 30-90s do clique até PDF pronto.

6. **Reprodutibilidade.** Mesma pasta Drive + mesmo commit da engine = mesmo PDF. Permite regerar edições antigas sem surpresas.

7. **Tolerância a duas convenções.** Engine aceita Gardens (plana) e Villa Park (subpastas). Migração orgânica, não forçada.

---

## Como rodar os testes

```bash
cd revista-engine
python3 tests/test_readers.py
```

Saída esperada: `41 passed, 0 failed`.

---

## Estado atual do projeto

```
revista-engine/
├── README.md                     ← este arquivo
├── docs/
│   ├── 00_HANDOFF.md             ← contexto + IDs do Drive
│   ├── 01_INVENTARIO_SECOES.md   ← catálogo das seções
│   ├── 02_INPUT_PACKAGE_SCHEMA.md
│   ├── 03_MIGRACAO_E_ADOCAO.md
│   └── 04_ARQUITETURA_CODIGO.md
├── engine/
│   ├── __init__.py
│   ├── models.py                 ← BadgeKind, Photo, PhotoGroup, packages, infer_badge
│   └── readers/
│       ├── __init__.py
│       ├── flat_folder.py        ← convenção Gardens
│       ├── sub_folders.py        ← convenção Villa Park
│       └── auto_detect.py        ← detector + dispatcher
├── tests/
│   └── test_readers.py           ← 41 testes
├── schemas/                      ← (vazio)
└── examples/                     ← (vazio)
```
