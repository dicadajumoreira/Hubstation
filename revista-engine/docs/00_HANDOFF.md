# HANDOFF — Revista Engine para Claude Code

> **Documento mestre de transferência.** Tudo que você precisa para continuar o projeto da Revista Engine no Claude Code.
> Este documento deve ser o primeiro arquivo que o Claude Code lê ao iniciar a sessão.

---

## 1. Contexto do projeto em 30 segundos

A **Sindicompany** (administradora de condomínios, brand `@sindicompanybr`) publica uma **revista mensal premium** para cada condomínio sob gestão. Hoje cada edição é produzida artesanalmente: a Juliana (operadora) conversa com Claude na web, manda fotos e textos, faz revisões iterativas até o PDF ficar bom. Funciona, mas não escala.

O objetivo é construir uma **engine genérica** em Python que:
- Lê pacotes de inputs estruturados do **Google Drive**
- Renderiza qualquer condomínio, qualquer empresa (Sindicompany ou outra administradora)
- Calcula páginas dinamicamente em função do conteúdo (nada de páginas hardcoded)
- Produz dois PDFs: A4 (impressão/desktop) e Mobile (smartphone-otimizado), com **paridade total** de conteúdo
- Liberta a Juliana de estar presente em cada edição

A revista tem **16 seções** documentadas, divididas em três tipos: editorial mensal compartilhado (igual para todos os condomínios do mês), específico do condomínio, e estrutural fixa.

**Stack:** Python puro (sem framework). Renderização final via Playwright (headless Chrome → PDF). Sem banco de dados — Drive é a fonte da verdade.

---

## 2. Quem é a interlocutora

**Juliana** (juliana@j2m.com.br). É a produtora editorial, conhece a revista por dentro, e foi quem fez todas as edições até agora artesanalmente. Comunicação dela é em **português brasileiro**, direta e visual — costuma identificar problemas com precisão olhando o PDF ("essa foto na página tal está sem badge"). Trabalha iterativamente: gera, revisa, aponta, ajusta.

Outras pessoas da equipe vão aprender a operar o sistema depois. Por isso o input package (Google Drive) precisa ser **à prova de erro humano**: validações claras, mensagens em português, células coloridas em vermelho quando faltar campo crítico.

---

## 3. Decisões já tomadas (NÃO renegociar sem motivo)

| Tema | Decisão |
|---|---|
| **Fonte dos inputs** | Google Drive com estrutura `Mês > Condomínio > _Editorial Mensal` |
| **Quem opera** | Equipe Sindicompany (Juliana hoje, equipe ampliada depois) |
| **Páginas** | 100% dinâmicas — engine calcula em função do conteúdo, NUNCA recebe como input |
| **Generalidade** | Engine genérica, tema/branding em arquivo separado (`tema.yaml`) |
| **Conteúdo dual** | Pacote editorial mensal compartilhado + pacote do condomínio específico |
| **Formatos** | A4 (794×1123 CSS) + Mobile (540×960 CSS @2x = 1080×1920 efetivo) |
| **Paridade** | Mobile carrega 100% do conteúdo do A4, layout próprio (não é A4 reduzido) |
| **Convenções de input** | Engine aceita 2: subpastas (Villa Park) **e** plana (Gardens). Sem big-bang de migração. |
| **Inferência de badges** | Automática por palavras-chave no nome — sem prefixos forçados |
| **Override de badges** | Tag `[engenharia]` no fim do nome força o badge específico |
| **Config** | Google Sheets com abas (NÃO YAML — equipe operadora usa Sheets) |
| **Pré-revisão** | Skill Humanizer + revisão pt-BR rodam automaticamente nos textos |
| **CAPS LOCK badges** | Renderizado via CSS, equipe pode escrever pasta como minúscula |
| **Hierarquia Drive** | Mantida igual ao que já existe (`Mês/Condomínio/`) |
| **Migração** | Sem big-bang — edições antigas ficam, novas adotam padrão final gradualmente |
| **Sem banco de dados** | Drive é fonte da verdade. Cache local opcional. |

---

## 4. Drive — IDs e links importantes

Toda a estrutura está em juliana@j2m.com.br. A Juliana é dona dos arquivos.

### 4.1 Pasta-mãe das revistas
- **Nome:** `Revistas`
- **ID:** `1AbO4d98pRDGDDaR9CNd3DU-s3nVkR2eN`
- **Link:** https://drive.google.com/drive/folders/1AbO4d98pRDGDDaR9CNd3DU-s3nVkR2eN

Estrutura interna observada:
```
Revistas/
├── 04 - 2026/                        ← edição publicada (PDFs prontos)
│   ├── Gardens Living/               ← convenção plana (fotos soltas + .txt)
│   ├── Villa Park Osasco/            ← convenção com subpastas
│   ├── Club Park Butantã/
│   └── (outros condomínios)
├── 05 - 2026/                        ← edição em produção (criada hoje)
│   ├── _Editorial Mensal/            ← NOVO (criamos esta sessão)
│   └── Gardens Living/               ← NOVO (criamos esta sessão)
├── Revistas Antigas/                 ← arquivamento (engine ignora)
└── Testes/                           ← sandbox (engine ignora)
```

### 4.2 Pasta `05 - 2026/` (edição em produção)
- **ID:** `1W0sI-OAL6G_9dsi-UBgp-d1LlGpZKqEk`

### 4.3 Pasta `_Editorial Mensal/05 - 2026/` (criada nesta sessão)
- **ID:** `1piBtHJaAg9VQLjUaPq1BPnqMMP3nPmhT`
- **Conteúdo:**
  - Doc `_LEIA-ME Editorial Mensal` (instruções de preenchimento)
  - Sheet `Editorial Mensal - 05.2026` (ID: `1ODty46lsGYi_NPuHhYiojZiApTlJYCkKQkps8tMVA1c`) — vazia, equipe cria 5 abas
  - Subpasta `Matéria de Capa/` (ID: `1OIgy1jpZN1Mslcxe85drb_Ui5Vxd3uPT`) com Doc `Texto - Matéria de Capa`
  - Subpasta `Agenda Cultural/` (ID: `1QgwkUstEEE3fflrot4OWsoR01uavjyBH`) com Doc `Texto - Agenda Cultural`
  - Subpasta `Receita do Mês/` (ID: `1kSLlNYqSGKjDpXGw3BLe4I2slL0f2mNQ`) com Doc `Texto - Receita do Mês`
  - Subpasta `Vida Condominial/` (ID: `1wuFlfrsyVRgLufMqdhnDu98OuxgUHYIi`) com Doc `Texto - Vida Condominial` ← seção S12B nova

### 4.4 Pasta `Gardens Living/05 - 2026/` (template do primeiro condomínio)
- **ID:** `1joWCNCSO0aSUaeVReSGQsq6JuY48KkLz`
- **Conteúdo:**
  - Doc `_LEIA-ME Pacote Gardens` (ID: `1_QyjdKs6BOZclf3PETP2OEu4xT970bJ0soXhgH3E2L8`) — instruções
  - Sheet `Config Gardens - 05.2026` (ID: `1MMIB8AR2V9jrJFlYLVuQDOSzkdqXjRCeZH1D5yRVOkc`) — **PARCIALMENTE PREENCHIDA** com Identificação, Síndicos, Carta. Aba "Nossos Números" tem só `prestacao_contas_url` apontando errado para a própria pasta da edição (precisa apontar para a pasta de prestação de verdade). Aba "Advertências" tem placeholders.
  - Doc `Texto - Carta do Síndico` (ID: `15gacdbslUkf_cHXRxbQejlcyJl8VOAY9yxjSptOTgD4`) — formulário com instruções, AINDA NÃO PREENCHIDA
  - Subpasta `Foto Sindico/` (ID: `1XtoOTRD0f-fqDAyqx08aK3lSWUYdMTea`) — vazia
  - Subpasta `_Eventos/` (ID: `1_Dt2-mZgKT-av95-3uVMwLEBfOOHdpCB`) — vazia

### 4.5 Pasta `Gardens Living/04 - 2026/` (revista publicada — caso de teste real)
- **ID:** `15DirBFlk18cbm6sPP8il89u2brxob0cA`
- **Importante:** esta é a melhor pasta para usar como **fixture real** ao testar a engine. Contém:
  - PDFs já publicados (A4 e Mobile) — referência visual da paridade
  - Convenção plana (fotos `.jpg` soltas + arquivos `.txt` cujo nome é a descrição)
  - PDF `Gardens Living Club - Financeiro.pdf` — dashboard Power BI consolidado (NÃO mensal — ver pendência abaixo)
  - PDF `Ocorrências Solucionadas - 03.2026.pdf` — relatório de manutenções operacionais (NÃO advertências)

### 4.6 Pasta `Villa Park Osasco/04 - 2026/` (segundo caso de teste real)
- Convenção com subpastas: `Manutenção Jardim/`, `Iluminação da Cancela/`, `Solda do Portão/`, `Reparo de Tubulação/`, `Manutenção Preventiva de Bombas/`, `Substituição da Esteira da Academia/`, `Reparo motor de saída veicular/`, `Dedetização e desratização/`
- Buscar via: `Google Drive:search_files` com `parentId` de `04 - 2026`

### 4.7 Arquivo "Untitled" perdido (deletar)
- **ID:** `157kE_AOo_B_6jIhs6cBJFjokXuG1O1EO`
- **Link:** https://drive.google.com/file/d/157kE_AOo_B_6jIhs6cBJFjokXuG1O1EO/view
- Resíduo de uma chamada de criação que falhou. **Pode deletar.**

---

## 5. Próximas frentes (em ordem de prioridade)

### Frente A — Camada de Drive (PRIORIDADE ALTA)

A engine hoje só lê pastas locais. Precisa de uma camada `engine/drive/` que:

1. **Resolve uma pasta de edição** a partir de "Gardens Living + 05/2026"
2. **Baixa em paralelo** todas as fotos via gdown (`pip install gdown`) ou Drive API
3. **Lê Sheets** via Drive API → converte para dict de abas
4. **Lê Docs** via Drive API → converte para markdown ou texto
5. **Cacheia localmente** em `/tmp/revista-engine-cache/` para não rebaixar
6. **Devolve** um diretório local pronto para os readers atuais consumirem

**Decisões pendentes desta camada:**
- Auth: gdown (OAuth do usuário) ou Drive API (service account)?
- TTL do cache: 1h? Sempre revalidar via mtime?
- Como lidar com mudanças no Drive durante a geração? (Lock? Snapshot?)

**Sugestão:** começar com gdown porque a Juliana já tem auth Google ativa. Service account vem depois se virar API server.

### Frente B — Primeiras seções do código (após Frente A)

Implementar 5 seções "fáceis" para validar o pipeline end-to-end:

1. **Contracapa** — estrutural fixa, ideal primeiro teste
2. **Expediente** — texto + créditos
3. **Capa** — 1 página, foto + manchete
4. **Carta do Síndico** — texto + foto
5. **Nossos Números** — KPIs + tabela de despesas

### Frente C — Camada de prestação de contas → Sheet (descoberta nesta sessão)

A Juliana quer enviar **PDFs de prestação de contas** todo mês na pasta da revista, e a engine extrai os valores financeiros automaticamente para popular a Sheet "Nossos Números".

**Pendência com a usuária:** definir o padrão de PDFs mensais que ela vai enviar.

### Frente D — Tema desacoplado (validar generalidade)

Hoje toda lógica de cores, fontes, paleta está hardcoded nas skills antigas. Migrar para `engine/theme/` carregando de `tema-sindicompany.yaml`. Provar com um `tema-generico.yaml` para outra empresa.

---

## 6. Skills antigas como referência (importante!)

A Juliana tem 4 skills no Drive da claude.ai que contêm **todo o conhecimento editorial visual** acumulado nas edições anteriores. **Não usar diretamente — referência apenas.** A engine genérica reescreve em estrutura limpa.

Skills disponíveis (em `/mnt/skills/user/` quando rodar via web):
- `sindicompany-revista` — skill genérica geral (mais completa, ~1300 linhas)
- `revista-sindicompany-04-2026` — específica da edição abril
- `revista-sindicompany-abril-2026` — duplicata da anterior

Conteúdo relevante das skills para portar à engine:
- Paleta de cores Sindicompany (Onix `#1A1C29`, Sand `#DABDA9`, Mint `#84C7D3`, etc.)
- Tipografia (Provicali para títulos, Epilogue para corpo)
- Layout de cada seção em CSS
- Helpers de imagem (`foto_jardim()`, `foto_legenda()`)
- URLs de assets no GitHub (`https://raw.githubusercontent.com/dicadajumoreira/Sindicompany/main/`)

---

## 7. Pendências da última sessão

1. **Sheet "Config Gardens - 05.2026"** está parcialmente preenchida. Aba "Nossos Números" tem `prestacao_contas_url` apontando para a pasta errada.

2. **Doc "Texto - Carta do Síndico"** ainda não foi escrito pela Juliana.

3. **Foto do(s) síndico(s)** ainda não foi subida em `Foto Sindico/`.

4. **Subpastas de manutenção do Gardens 05/2026** ainda não foram criadas.

5. **Padrão de PDFs mensais de prestação** ficou em aberto (ver Frente C).

6. **Arquivo "Untitled"** na raiz do Drive da Juliana precisa ser deletado (ID `157kE_AOo_B_6jIhs6cBJFjokXuG1O1EO`).

---

## 8. Filosofia de trabalho com a Juliana

- **Comunicação em português brasileiro.** Tom direto, sem encheção de linguiça. Ela é executiva, valoriza objetividade.
- **Ela revisa visualmente.** Sempre que possível, gere um PDF de exemplo e mostre. Ela aponta com precisão o que está errado.
- **Decisões dela são definitivas.** Quando ela diz "ok" ou "perfeito", segue em frente.
- **Ela aceita propostas concretas.** Em vez de "como você quer fazer?", proponha "vou fazer X assim, ok?".
- **Ela tem padrão estético alto.** A revista é premium. Espaçamento generoso, tipografia editorial, sem cara de PowerPoint corporativo.
- **Ela não é desenvolvedora.** Use Sheets para configs, Docs para textos, pastas para fotos.

---

## 9. Pontos de atenção / armadilhas conhecidas

1. **CAPS LOCK dos badges** — equipe escreve a pasta com `[jardim]` em minúscula, badge renderiza `JARDIM` via CSS. NÃO normalize na escrita.

2. **Pré-revisão automática** — Skill Humanizer + revisão pt-BR rodam em textos do condomínio (carta, descrições) antes de gerar PDF. NÃO aplicar em: nomes próprios, dados numéricos, badges.

3. **Convenção plana (Gardens)** — janela de 48h é o sweet spot. Já testei 15min (muito restrito) e quebrava agrupamentos válidos. Não diminua.

4. **Subpastas vazias** — `SubFoldersReader` ignora silenciosamente.

5. **Nome com prefixo numérico** — `01_Pintura Hall/` deve render como "Pintura Hall" (sem o prefixo). Implementar quando chegarmos à camada de seções.

6. **Mobile NÃO é A4 reduzido** — a paridade é de **conteúdo**, não de **layout**.

7. **Outros condomínios podem ter Sheet de config diferente.** Por enquanto só o Gardens tem o template.

---

## 10. Glossário

- **Edição** = uma revista de um condomínio em um mês específico (ex: Gardens 05/2026)
- **Pacote editorial mensal** = conteúdo compartilhado entre todos os condomínios daquele mês
- **Pacote do condomínio** = conteúdo específico daquele condomínio em uma edição
- **Seção** = uma das 16 partes da revista (Capa, Carta, Matéria de Capa, etc.)
- **Badge** = etiqueta visual em foto de manutenção (JARDIM, ENGENHARIA, etc.)
- **Display size** = tamanho do destaque de um grupo de fotos (hero, large, small)
- **PhotoGroup** = grupo de fotos com título, descrição e badge (uma manutenção/evento)
- **Convenção plana** = estilo Gardens (fotos soltas + .txt-descrição)
- **Convenção subfolders** = estilo Villa Park (subpastas por manutenção)
- **Síndico** = administrador do condomínio (assina a Carta da revista)
