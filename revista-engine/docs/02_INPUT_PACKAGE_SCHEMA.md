# Revista Engine — Schema do Pacote de Inputs (Google Drive)

> **Versão 2** — alinhada à estrutura real do Drive da Sindicompany.
> Substitui a v1, que propunha hierarquia Condomínio>Mês. A hierarquia
> real e mantida é **Mês>Condomínio**.

---

## 1. Hierarquia (a real, mantida do Drive atual)

```
📁 Revistas/                              ← pasta-mãe (já existe)
│  ID: 1AbO4d98pRDGDDaR9CNd3DU-s3nVkR2eN
│
├── 📁 MM - YYYY/                          ← edição mensal (ex.: "04 - 2026")
│   ├── 📁 [Nome do Condomínio]/           ← uma pasta por condomínio do mês
│   ├── 📁 [Nome do Condomínio 2]/
│   ├── 📁 _Editorial Mensal/              ← NOVO: pacote compartilhado do mês
│   └── (PDFs auxiliares soltos — POPs, conversas, etc., ignorados pela engine)
│
├── 📁 Revistas Antigas/                   ← arquivamento (engine ignora)
└── 📁 Testes/                             ← sandbox (engine ignora)
```

**Vantagem da hierarquia atual:** todas as edições do mês ficam visualmente próximas. Quando bate o dia 25, a Juliana abre `04 - 2026/` e vê de relance quais condomínios já fecharam o pacote e quais ainda estão pendentes.

**Convenção de nome da pasta de mês:** `MM - YYYY` (ex.: `04 - 2026`, `05 - 2026`). Mantém o padrão atual exatamente.

---

## 2. Pacote A — Editorial Mensal (NOVO, compartilhado)

Localização: `📁 Revistas/04 - 2026/_Editorial Mensal/`

Esta é uma pasta nova que precisa ser criada. Por convenção começa com `_` para ficar **no topo da listagem alfabética**, separada visualmente das pastas de condomínios.

```
_Editorial Mensal/
│
├── 📊 Editorial Mensal               (Google Sheet — config + textos curtos)
│
├── 📁 Matéria de Capa/
│   ├── 📄 Texto                      (Google Doc com kicker, manchete, corpo, fontes)
│   └── foto-principal.jpg            (foto principal)
│
├── 📁 Agenda Cultural/
│   ├── 📄 Texto                      (Google Doc com hero + cards secundários)
│   └── foto-hero.jpg
│
├── 📁 Receita do Mês/
│   ├── 📄 Texto                      (Google Doc com ingredientes + preparo)
│   └── foto-receita.jpg
│
└── (Dicas, Curiosidades, Legislação e Signos vão direto na Sheet, são textuais)
```

**Por que tudo numa Sheet quando possível?** Porque a Juliana e equipe vão preencher mês a mês. Sheet com células é mais à prova de erro que Doc com formatação. Apenas seções que precisam de imagem (Matéria de Capa, Agenda, Receita) ganham subpasta própria.

### Estrutura da Sheet "Editorial Mensal"

5 abas:

**Aba 1 — Geral**

| chave            | valor               |
|------------------|---------------------|
| mes              | Maio                |
| ano              | 2026                |
| numero_edicao    | 5                   |

**Aba 2 — Dicas Práticas** (6 a 8 linhas)

| numero | titulo                  | corpo                                         |
|--------|-------------------------|-----------------------------------------------|
| 1      | Cuide do bem comum      | Reporte falhas de iluminação à administração. |
| 2      | Respeite o silêncio     | ...                                           |

**Aba 3 — Curiosidades** (4 a 5 linhas)

| fato                    | contexto                  | fonte    |
|-------------------------|---------------------------|----------|
| 25% dos brasileiros...  | dado sobre habitação...   | IBGE 2025|

**Aba 4 — Novidades e Legislação** (3 linhas)

| badge        | titulo                | data       | resumo               | fonte         |
|--------------|-----------------------|------------|----------------------|---------------|
| LEGISLAÇÃO   | Nova lei de pet...    | 12/05/2026 | Texto da notícia...  | SECOVI-SP     |

**Aba 5 — Signos** (12 linhas, uma por signo)

| signo       | texto_previsao                                          |
|-------------|---------------------------------------------------------|
| Áries       | Mês de movimento e novos contatos profissionais...      |
| Touro       | Foco em estabilidade financeira e relacionamentos...    |

---

## 3. Pacote B — Condomínio (mantém estrutura atual + leve evolução)

Localização: `📁 Revistas/04 - 2026/Gardens Living/`

A engine aceita **as duas convenções** que vocês já usam, com preferência pela com subpastas (Villa Park) para edições novas:

### 3.1 Convenção A — Plana (Gardens 04/2026)

```
Gardens Living/
├── 📊 Config Gardens                     (Google Sheet — dados do condomínio)
├── PHOTO-2026-03-30-11-23-12.jpg         (foto avulsa)
├── PHOTO-2026-03-30-11-22-56.jpg
├── Nova restauração da grama ao lado do banheiro e cozinha.txt
├── Árvore novo no condomínio.txt
├── (mais fotos e txts soltos)
│
└── (PDFs gerados: Revista_..._A4.pdf, Revista_..._Mobile.pdf)
```

**Como a engine interpreta:**
- Cada `.txt` cujo **nome** parece uma descrição (>20 caracteres) → vira uma "manutenção/evento"
- Fotos próximas em data e similaridade são **agrupadas automaticamente** com o `.txt` mais próximo
- Sem `.txt`: foto entra como avulsa numa galeria coletiva, sem legenda

### 3.2 Convenção B — Subpastas (Villa Park 04/2026, recomendada)

```
Villa Park Osasco/
├── 📊 Config Villa Park                  (Google Sheet — dados do condomínio)
│
├── 📁 Manutenção Jardim/
│   ├── foto-1.jpg
│   ├── foto-2.jpg
│   └── 📄 Descrição                      (Google Doc, opcional)
│
├── 📁 Substituição da Esteira da Academia/
│   ├── foto-1.jpg
│   └── foto-2.jpg
│
├── 📁 Manutenção Preventiva de Bombas/
├── 📁 Iluminação da Cancela/
├── 📁 Reparo de Tubulação/
│
└── (PDFs gerados)
```

**Como a engine interpreta:**
- Cada subpasta = uma manutenção/evento
- Nome da subpasta = título da seção (renderizado em **CAIXA ALTA** automaticamente nos badges)
- Quantidade de fotos define o destaque (regra do doc 01: 6+ → página inteira, 3-5 → card grande, 1-2 → card pequeno)
- Doc "Descrição" dentro da subpasta (opcional) vira descrição/legenda longa

### 3.3 Detecção automática de tipo (badge)

A engine **infere o tipo de badge** a partir de palavras-chave no nome da pasta. Sem prefixo `[tipo]`, sem fricção:

| Palavras-chave no nome             | Badge aplicado     | Helper visual          |
|------------------------------------|--------------------|------------------------|
| jardim, paisagismo, grama, planta  | mint pill "JARDIM" | `foto_jardim()`        |
| fachada, engenharia, vistoria      | dark "ENGENHARIA"  | `foto_legenda()`       |
| operacional, manutenções (visita)  | mint "OPERACIONAL" | `foto_legenda()`       |
| segurança, câmera, portaria, alarme| onix "SEGURANÇA"   | `foto_legenda()`       |
| pintura, reparo, troca, instalação | mint "MANUTENÇÃO"  | `foto_legenda()`       |
| (qualquer outro)                   | mint "MANUTENÇÃO"  | `foto_legenda()`       |

Exemplos reais do Villa Park:
- `Manutenção Jardim` → palavra-chave "Jardim" → badge JARDIM (pill mint com folha)
- `Iluminação da Cancela` → palavra-chave nenhuma específica → badge MANUTENÇÃO default
- `Reparo motor de saída veicular` → palavra-chave "Reparo" → badge MANUTENÇÃO
- `Solda do Portão` → default → badge MANUTENÇÃO
- (numa edição futura) `Vistoria de Fachada` → "Fachada" → badge ENGENHARIA

A Juliana pode override manualmente colocando uma tag entre colchetes no fim do nome se quiser forçar:
- `Pintura do Hall Social [engenharia]` → força badge ENGENHARIA mesmo sem palavra-chave

---

## 4. Estrutura da Sheet "Config [Condomínio]"

Cada condomínio tem sua própria Sheet de config. 5 abas:

### Aba 1 — Identificação

| chave                          | valor                               |
|--------------------------------|-------------------------------------|
| condominio.nome                | Gardens Living Club                 |
| condominio.nome_curto          | Gardens                             |
| condominio.unidades_total      | 312                                 |
| condominio.cidade              | São Paulo                           |
| condominio.bairro              | Vila Nova Conceição                 |
| edicao.numero                  | 5                                   |
| edicao.ano                     | 2026                                |
| edicao.tema_capa_override      | (vazio = usa o tema do mês)         |
| edicao.manchete_override       | (vazio = usa a manchete do mês)     |

### Aba 2 — Síndico(s)

| ordem | nome              | genero    | cargo                    | foto_filename       | object_position |
|-------|-------------------|-----------|--------------------------|---------------------|-----------------|
| 1     | Gustavo Rosendo   | masculino | Síndico Profissional     | sindico-rosendo.jpg | center 20%      |
| 2     | Gustavo Barco     | masculino | Síndico Profissional     | sindico-barco.jpg   | center 20%      |

A linha 1 (ordem=1) é quem assina a Carta. Linhas seguintes só aparecem no Expediente.

### Aba 3 — Carta do Síndico

Texto longo numa única célula, ou referência a um Doc separado:

| chave        | valor                                                                |
|--------------|----------------------------------------------------------------------|
| carta_texto  | (cole aqui as 350-450 palavras, OU)                                  |
| carta_doc_id | 1ABCxyz...                                                           |

### Aba 4 — Nossos Números

KPIs do mês:

| chave              | valor      |
|--------------------|------------|
| receita_brl        | 245000.00  |
| despesas_brl       | 198500.00  |
| fundo_reserva_brl  | 1250000.00 |
| inadimplencia_pct  | 3.2        |

E uma sub-tabela de despesas (mesma aba, abaixo dos KPIs):

| categoria   | valor_brl | observacao         |
|-------------|-----------|--------------------|
| Pessoal     | 78000.00  | Folha + encargos   |
| Limpeza     | 12500.00  |                    |
| Energia     | 18200.00  | Áreas comuns       |

### Aba 5 — Advertências

| chave                | valor   |
|----------------------|---------|
| total_advertencias   | 8       |
| total_multas         | 2       |
| valor_multas_brl     | 850.00  |

E uma sub-lista dos assuntos recorrentes (uma linha por assunto):

| assunto                           |
|-----------------------------------|
| Barulho após 22h                  |
| Animais fora da coleira no hall   |
| Uso indevido do salão de festas   |

---

## 5. Como a engine consome os pacotes

```
1. Equipe roda comando:
   "Gerar revista 05/2026 do Gardens Living"

2. Engine resolve as duas pastas no Drive:
   📁 Revistas/05 - 2026/_Editorial Mensal/
   📁 Revistas/05 - 2026/Gardens Living/

3. Engine baixa em paralelo (gdown + Drive API):
   - Sheet "Editorial Mensal" → JSON
   - Subpastas com imagens → fotos baixadas
   - Sheet "Config Gardens" → JSON
   - Subpastas de manutenção → fotos baixadas
   - .txt soltos (convenção plana) → fotos próximas agrupadas

4. Engine valida o pacote:
   ✓ Quais seções estão completas?
   ⚠ Avisos: foto pequena, ausente, etc.
   ✗ Bloqueios: campos críticos vazios

5. Engine inferi badges, paginação dinâmica, monta a revista

6. Engine sobe os PDFs no Drive:
   📁 Revistas/05 - 2026/Gardens Living/
      ├── Revista_Gardens_Living_Edicao_05_2026_A4.pdf
      └── Revista_Gardens_Living_Edicao_05_2026_Mobile.pdf
```

---

## 6. Pré-revisão automática (resposta ao ponto 2 da Juliana)

Antes de gerar o PDF final, a engine roda dois passes nos textos do condomínio:

1. **Skill Humanizer** — remove marcas de prosa de IA, polir tom editorial
2. **Revisão de pt-BR** — acentos, concordância, regência, vícios

Aplica em: Carta do Síndico, descrições/legendas de manutenções e eventos, observações nas advertências.

**Não aplica em:** dados numéricos (números, KPIs), nomes próprios, badges. Esses passam intactos.

A pré-revisão é configurável no `config.tema`:

```
revisao_pt_br_automatica: true     (default, recomendado)
humanizer_automatico: true          (default, recomendado)
```

Se a equipe quiser publicar mais rápido sem revisão, basta desligar.

---

## 7. Histórico permanente

Mantido como hoje: cada edição mensal vira uma pasta `MM - YYYY` no `Revistas/`. Edições antigas migram para `Revistas Antigas/` quando a Juliana achar conveniente. A engine ignora `Revistas Antigas/` e `Testes/` automaticamente.

---

## 8. Replicação para outros condomínios — e outras empresas

**Novo condomínio na Sindicompany:**
1. Criar pasta com o nome do condomínio dentro de `MM - YYYY/`
2. Criar Sheet "Config [Nome]" duplicando da Gardens
3. Preencher e mandar gerar

**Outra empresa (não Sindicompany):**
1. Criar uma nova pasta-mãe paralela (ex.: `Revistas - Outra Administradora/`)
2. Configurar tema próprio em `_Tema da Marca/` (separadamente)
3. Mesma estrutura interna funciona — a engine carrega o tema da empresa que está sendo gerada

A engine continua agnóstica de marca; só o tema muda.

---

## 9. Resumo das mudanças vs v1

| Aspecto              | v1 (proposta inicial)        | v2 (alinhada à realidade)              |
|----------------------|------------------------------|----------------------------------------|
| Hierarquia           | `Condomínio/Mês/`            | **`Mês/Condomínio/`** (mantém atual)   |
| Editorial Mensal     | Pasta separada de tudo       | Subpasta `_Editorial Mensal/` no mês   |
| Convenção fotos      | Subpastas com prefixo `[]`   | **Subpastas com nome livre**, badge inferido |
| Convenção legacy     | Não suportada                | **Suporta convenção plana da Gardens** |
| Config               | YAML embarcado em Doc        | **Google Sheet** com abas              |
| Nome pasta mensal    | `2026-05 Maio`               | **`05 - 2026`** (formato MM - YYYY)    |
