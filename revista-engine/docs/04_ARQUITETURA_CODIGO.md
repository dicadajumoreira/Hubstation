# Revista Engine — Arquitetura do Código

> **Versão 1** — primeira camada (readers) implementada e testada.
> Status atual: 41/41 testes passando.

---

## 1. Princípio de design

Engine separada em **camadas finas**, cada uma com uma responsabilidade clara. Camadas dependem só das camadas abaixo, nunca de cima:

```
┌───────────────────────────────────────────┐
│  CLI / Web / Claude                       │   ← interface
└───────────────────────────────────────────┘
                  ↓
┌───────────────────────────────────────────┐
│  Engine Orchestrator                      │   ← orquestração
│  (gera revista de A a Z)                  │
└───────────────────────────────────────────┘
                  ↓
┌───────────────────────────────────────────┐
│  Sections (15 classes)                    │   ← renderização por seção
│  cada uma: validate, paginate, render     │
└───────────────────────────────────────────┘
                  ↓
┌───────────────────────────────────────────┐
│  Composer + Renderer                      │   ← junta páginas, gera PDF
└───────────────────────────────────────────┘
                  ↓
┌───────────────────────────────────────────┐
│  Models + Readers                         │   ← FUNDAÇÃO (já implementada)
│  (representação dos dados +               │
│   leitura do Drive em pastas locais)      │
└───────────────────────────────────────────┘
```

Cada camada tem testes próprios. Mudanças em camadas altas não quebram camadas baixas.

---

## 2. Estrutura de arquivos atual

```
revista-engine/
├── README.md
├── docs/                          ← especificação
│   ├── 01_INVENTARIO_SECOES.md
│   ├── 02_INPUT_PACKAGE_SCHEMA.md
│   ├── 03_MIGRACAO_E_ADOCAO.md
│   └── 04_ARQUITETURA_CODIGO.md   ← este doc
│
├── engine/                        ← código Python
│   ├── __init__.py
│   ├── models.py                  ← ✅ implementado
│   └── readers/                   ← ✅ implementado
│       ├── __init__.py
│       ├── flat_folder.py         ← convenção Gardens
│       ├── sub_folders.py         ← convenção Villa Park
│       └── auto_detect.py         ← detector + dispatcher
│
├── tests/
│   └── test_readers.py            ← ✅ 41 testes, todos passando
│
├── examples/                      ← (vazio por enquanto)
└── schemas/                       ← (vazio por enquanto)
```

Próximas adições previstas:

```
engine/
├── theme/                         ← carregamento de tema
├── drive/                         ← integração Drive (gdown + Sheets API)
├── package_loader.py              ← junta tudo em CondominiumPackage
├── sections/                      ← uma classe por seção (15 arquivos)
│   ├── base.py                    ← Section abstrata
│   ├── cover.py
│   ├── letter.py
│   ├── our_condo_maintenance.py
│   └── ... (+12)
├── composer.py                    ← empilha páginas, calcula numeração
├── renderer.py                    ← Playwright → PDF (A4 + Mobile)
├── pre_review.py                  ← Humanizer + revisão pt-BR
└── orchestrator.py                ← pipeline end-to-end
```

---

## 3. Camada de modelos (`engine/models.py`)

**O que é:** dataclasses imutáveis que representam os inputs depois de lidos do Drive. Desacoplam totalmente a fase de leitura da fase de renderização.

**Tipos principais:**

| Tipo                  | Representa                                                |
|-----------------------|-----------------------------------------------------------|
| `BadgeKind` (Enum)    | Tipos de badge: JARDIM, ENGENHARIA, OPERACIONAL, etc.     |
| `infer_badge(name)`   | Função pura — infere badge a partir de palavras-chave     |
| `Photo`               | Uma foto carregada (path local, drive_id, tamanho)        |
| `PhotoGroup`          | Grupo de fotos (manutenção/evento) com title, description, badge |
| `CondominiumPackage`  | Pacote completo do condomínio para uma edição             |
| `EditorialPackage`    | Pacote editorial mensal compartilhado                     |

**Regra crítica do `PhotoGroup`:** a property `display_size` codifica a regra de paginação dinâmica descoberta nas edições reais:

```python
@property
def display_size(self) -> str:
    n = self.num_photos
    if n >= 6: return "hero"   # página inteira
    if n >= 3: return "large"  # card grande, 1 por página
    return "small"             # card pequeno, até 2 por página
```

A engine **não toma decisão de paginação no código de renderização** — ela pergunta ao `PhotoGroup` qual o display_size e renderiza de acordo. Isso mantém a regra em um único lugar.

---

## 4. Camada de readers (`engine/readers/`)

**Responsabilidade:** ler uma pasta local (já baixada do Drive) e produzir uma lista de `PhotoGroup`. Nenhum reader sabe sobre Drive — eles só leem do disco local. A integração com Drive fica numa camada acima.

### 4.1 `FlatFolderReader` (convenção Gardens)

Pasta com fotos `.jpg` soltas + arquivos `.txt` cujo **nome** é a descrição.

**Algoritmo:**
1. Lista todos os arquivos da pasta (não recursivo)
2. Separa em: imagens, .txt-descrição (>20 chars), outros
3. Para cada foto, identifica o `.txt` **mais próximo** em timestamp dentro de uma janela de 48h (default)
4. Cada foto é atribuída a no máximo um `.txt` (o mais próximo)
5. Fotos sem `.txt` próximo viram um grupo "Outros Registros do Mês"

**Detalhes:**
- Timestamp da foto: extrai do nome (`PHOTO-YYYY-MM-DD-HH-MM-SS`) ou usa `mtime`
- Timestamp do txt: usa `mtime` (data de upload no Drive)
- Janela default 48h: tolerante o bastante para fotos batidas em horários espalhados, restritivo o bastante para não confundir manutenções diferentes
- Nome do `.txt` é limpo (quebras de linha, espaços múltiplos, ponto final)

### 4.2 `SubFoldersReader` (convenção Villa Park)

Pasta com subpastas, cada subpasta = uma manutenção/evento. Mais explícita.

**Algoritmo:**
1. Lista subpastas diretas (não recursivo)
2. Ignora subpastas que começam com `.` ou `_OUTPUT`
3. Para cada subpasta:
   - Nome da subpasta = título do grupo
   - Fotos dentro = fotos do grupo
   - `.txt` ou `.md` dentro = descrição longa (opcional)
   - Badge inferido do título
4. Subpastas sem fotos são ignoradas silenciosamente

### 4.3 `auto_detect.detect_convention()` + `read_groups()`

Detecta qual convenção a pasta está usando e despacha para o reader correto.

**Regras:**
- ≥3 subpastas com fotos → `subfolders`
- ≥3 `.txt`-descrição na raiz → `flat`
- Ambos → `mixed` (mescla, prefere subpastas para títulos duplicados)
- Pouco material → default `flat`

A função `read_groups(folder)` retorna `(grupos, convencao_detectada)` para a camada acima saber qual leitura foi feita.

---

## 5. Inferência de badges (`infer_badge`)

Função pura, sem efeitos colaterais. Recebe o nome (de pasta ou descrição) e retorna o `BadgeKind`.

**Tabela de palavras-chave** (ordem importa — primeira que casa vence):

| Ordem | Badge       | Palavras-chave                                            |
|-------|-------------|-----------------------------------------------------------|
| 1     | JARDIM      | jardim, paisagismo, grama, planta, arvore                 |
| 2     | ENGENHARIA  | fachada, engenharia, vistoria, estrutura                  |
| 3     | SEGURANCA   | seguranca, camera, portaria, alarme, cancela, portao      |
| 4     | OPERACIONAL | operacional, visita, inspecao                             |
| 5     | MANUTENCAO  | pintura, reparo, troca, instalacao, manutencao, ...       |
| -     | (default)   | MANUTENCAO                                                |

**Override manual:** se o nome terminar com `[tag]` (ex: `Pintura do Hall [engenharia]`), a tag entre colchetes ganha precedência sobre as palavras-chave.

**Normalização:** lowercase + remoção de acentos antes de buscar palavras-chave. `"Manutenção Jardim"` casa com `"jardim"` mesmo com acento e maiúscula.

---

## 6. Testes (`tests/test_readers.py`)

**Filosofia:** testes que reproduzem nomes e estruturas REAIS vistos no Drive. Cada teste é uma simulação concreta de um caso real.

**Cobertura atual (41 testes):**

| Suite                                | Testes |
|--------------------------------------|--------|
| `infer_badge` (cases reais Villa Park + Gardens) | 15 |
| `SubFoldersReader` (Villa Park 04/2026 simulado) | 9  |
| `FlatFolderReader` (Gardens 04/2026 simulado)    | 9  |
| `auto_detect` (4 cenários)                       | 4  |
| `read_groups` (pipeline completo)                | 4  |

**Como rodar:**

```bash
python3 tests/test_readers.py
```

**Output:** verde para passou, vermelho para falhou, com mensagem de comparação. Sem framework externo (sem pytest, sem dependências) — mantém o setup zero.

---

## 7. Próxima camada: integração com Drive

A camada de readers funciona em pastas **locais**. Para usar dados reais do Drive, precisamos de uma camada `engine/drive/` que:

1. **Resolve uma pasta de edição** a partir de "Gardens Living + 04/2026"
2. **Baixa em paralelo** todas as fotos via `gdown`
3. **Lê Sheets** via Drive API e converte para dict
4. **Lê Docs** via Drive API e converte para texto
5. **Cacheia** localmente para não rebaixar a cada execução
6. **Devolve** um diretório local pronto para os readers consumirem

Depois disso, um `package_loader.py` junta tudo num `CondominiumPackage` ou `EditorialPackage`.

**Decisões pendentes para essa próxima camada:**

- Onde armazenar o cache local? (`/tmp/revista-engine-cache/`?)
- TTL do cache? (permitir override "sem cache" para testes)
- Auth: usar OAuth do gdown (já funciona) ou Drive API com service account?
- Quando o usuário muda algo no Drive, como invalidar cache? (mtime? hash?)

Essas decisões são para a próxima sessão.

---

## 8. Próxima camada: seções

Cada seção do inventário (Doc 01) vira uma classe Python que herda de `Section`:

```python
class Section(ABC):
    @abstractmethod
    def validate(self, inputs: dict) -> list[str]:
        """Retorna lista de erros (vazia se válido)."""

    @abstractmethod
    def paginate(self, inputs: dict) -> int:
        """Quantas páginas vai ocupar."""

    @abstractmethod
    def required_assets(self, inputs: dict) -> list[str]:
        """URLs de assets a baixar antes de renderizar."""

    @abstractmethod
    def render_a4(self, inputs: dict, theme: Theme) -> list[str]:
        """Lista de strings HTML, uma por página A4."""

    @abstractmethod
    def render_mobile(self, inputs: dict, theme: Theme) -> list[str]:
        """Lista de strings HTML, uma por página Mobile."""
```

A engine instancia uma classe por seção, chama `validate()` para coletar todos os erros, depois `paginate()` para calcular numeração, e por fim `render_a4()` + `render_mobile()` em paralelo.

Ordem prioritária de implementação (do mais simples ao mais complexo):

1. **Contracapa** (estrutural fixa, ideal para validar o pipeline)
2. **Expediente** (texto + créditos)
3. **Capa** (1 página, foto + manchete)
4. **Carta do Síndico** (texto + foto)
5. **Nossos Números** (KPIs + gráfico)
6. **Advertências** (dados agregados + dicas)
7. **Signos** (12 cards)
8. **Receita do Mês** (texto + foto + lista)
9. **Curiosidades** (cards)
10. **Novidades e Legislação** (notícias)
11. **Agenda Cultural** (hero + cards)
12. **Dicas Práticas** (lista numerada)
13. **Matéria de Capa** (2-4 páginas dinâmicas)
14. **Nosso Condomínio - Eventos**
15. **Nosso Condomínio - Manutenções** (mais complexa, paginação dinâmica de fotos)

---

## 9. Métricas de qualidade

Para considerar a Fase 1 "pronta", a engine precisa atingir:

- ✅ Camada de modelos + readers com testes (41/41 atualmente)
- ⏭ Geração de revista do Gardens 04/2026 a partir do Drive em <90s
- ⏭ Paridade visual de 90%+ com a edição artesanal já publicada
- ⏭ Mensagens de erro claras quando algo está faltando
- ⏭ Tema desacoplado do código (trocar Sindicompany por outra empresa via arquivo)
- ⏭ Documentação para a equipe operar sem precisar entender o código
