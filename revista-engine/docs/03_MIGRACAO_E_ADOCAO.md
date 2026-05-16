# Revista Engine — Estratégia de Migração e Adoção

> Como migrar do fluxo atual (Claude artesanal por edição) para a engine, **sem traumatizar a equipe** e sem reorganizar o Drive todo de uma vez.

---

## Princípio: zero big-bang

A engine **aceita as duas convenções** que vocês já usam (Gardens plana + Villa Park com subpastas). Isso é proposital. Migrar todos os condomínios para o "padrão ideal" antes de ligar a engine seria um projeto de duas semanas só de reorganização — ninguém quer isso.

Estratégia: a engine roda **a partir do que vocês já têm** e a equipe migra organicamente, edição por edição, conforme for confortável.

---

## Fase 1.1 — Engine roda no que existe (sem mudar nada no Drive)

**Objetivo:** provar que a engine consegue gerar a revista do Gardens 04/2026 (que já está pronta) a partir do Drive **exatamente como ele está hoje**, sem subpastas, com fotos soltas e .txt-como-descrição.

**O que precisa:**
- Engine implementa **dois readers**:
  - `FlatFolderReader` — convenção Gardens (fotos soltas + .txt cujo nome é a descrição)
  - `SubFoldersReader` — convenção Villa Park (subpastas por manutenção)
- Engine detecta automaticamente qual está em uso olhando a estrutura
- Equipe não precisa fazer nada — a engine se adapta

**Critério de sucesso:** rodar `gerar revista 04/2026 Gardens Living` e o PDF resultante ser visualmente equivalente ao que a Juliana já produziu artesanalmente (com pequenas diferenças aceitáveis enquanto a paridade fica madura).

**Por que isso importa:** valida que a engine entende a realidade. Se a engine só funciona com a convenção "ideal", ela vira mais um sistema rígido que ninguém usa.

---

## Fase 1.2 — Editorial Mensal sai do hardcoded

**Objetivo:** desacoplar o conteúdo editorial mensal compartilhado do código da engine.

**Mudança no Drive:** criar a pasta `_Editorial Mensal/` dentro de `04 - 2026/`. Preencher pela primeira vez com:
- Sheet "Editorial Mensal" com Dicas, Curiosidades, Legislação, Signos
- Subpasta "Matéria de Capa/" com Doc + foto
- Subpasta "Agenda Cultural/" com Doc + foto
- Subpasta "Receita do Mês/" com Doc + foto

**Quem preenche:** equipe editorial Sindicompany. Uma vez por mês. Reaproveita pra todos os condomínios do mês automaticamente.

**Tempo estimado de preenchimento mensal:** 1-2h (vs. atualmente, em que esse conteúdo é regenerado por Claude a cada revista).

**Critério de sucesso:** depois desta fase, gerar revista de qualquer condomínio do mês usa o `_Editorial Mensal/` automaticamente — sem rebuscar agenda/dicas/curiosidades.

---

## Fase 1.3 — Sheet de Config por condomínio

**Objetivo:** dados estruturados (KPIs, advertências, síndico) saem das mensagens do chat e viram input persistente.

**Mudança no Drive:** em cada pasta de condomínio do mês, adicionar uma Sheet "Config [Nome]" com as 5 abas (Identificação, Síndico, Carta, Números, Advertências).

**Quem preenche:** o gestor de cada condomínio (ou equipe da Sindicompany em nome dele). Pode ser uma pessoa por condomínio se vocês delegarem.

**Tempo estimado por condomínio:** 15-30 min (a maioria dos campos é estável entre meses; só os números e advertências mudam).

**Truque para acelerar:** a Sheet do mês 04 vira o template do mês 05 (basta duplicar). Só campos que mudaram precisam ser editados.

**Critério de sucesso:** zero coleta de dados via chat. A equipe abre Sheet, preenche, e a engine puxa direto.

---

## Fase 1.4 — Migração gradual para subpastas (Villa Park style)

**Objetivo:** padronizar todos os condomínios na convenção com subpastas.

**Estratégia:** **não fazer migração retroativa**. As edições antigas ficam como estão (tanto faz: já foram publicadas). A migração acontece **só nas novas edições**:

- Quando vocês forem montar a edição 05/2026 do Gardens, em vez de jogar fotos soltas, criem subpastas por manutenção
- Edições novas: já nascem no padrão Villa Park
- Edições antigas: ficam intactas no `Revistas Antigas/`

**Tempo de transição:** 1-2 meses. Em maio, alguns condomínios estarão em formato novo, outros ainda em formato antigo. Tudo bem — a engine entende os dois.

**Critério de sucesso:** em julho/2026, todos os condomínios estão usando subpastas naturalmente.

---

## Fase 1.5 — Geração via comando único

**Objetivo:** a equipe roda um comando, a engine faz o resto.

```bash
# Da máquina da Juliana (ou do site web no futuro):
revista-engine generate --mes 05-2026 --condo "Gardens Living"

# Output:
✓ Editorial Mensal carregado (8 itens)
✓ Config Gardens carregado
✓ 12 manutenções detectadas (8 com subpasta, 4 inferidas de .txt soltos)
⚠ Foto-síndico ausente — usando placeholder
✓ Renderizando A4... (45s)
✓ Renderizando Mobile... (38s)
✓ Upload para Drive concluído

📄 PDFs disponíveis:
   https://drive.google.com/.../Revista_Gardens_..._A4.pdf
   https://drive.google.com/.../Revista_Gardens_..._Mobile.pdf
```

**Critério de sucesso:** geração end-to-end em menos de 2 minutos, sem precisar de Claude no loop.

---

## Cronograma realista

| Fase | Duração | Quem trabalha          | Saída                              |
|------|---------|------------------------|------------------------------------|
| 1.1  | 2 sem   | Eu (engine)            | Engine roda no Drive como está     |
| 1.2  | 1 sem   | Equipe edit + eu       | `_Editorial Mensal/` operacional   |
| 1.3  | 1 sem   | Gestores de condo + eu | Sheets de config preenchidas       |
| 1.4  | 1-2 meses | Equipe (gradual)     | Todas edições novas em subpastas   |
| 1.5  | 1 sem   | Eu                     | CLI funcional                      |

**Total Fase 1:** ~6 semanas de trabalho técnico + 1-2 meses de adoção orgânica.

Após a Fase 1, a Fase 2 (web no domínio de vocês) começa com fundação sólida.

---

## Riscos e mitigações

### Risco 1: a paridade visual com a edição artesanal não bate

A primeira edição gerada pela engine vai ter diferenças pequenas em relação ao que a Juliana faria à mão. Algumas vão ser melhoria, outras vão ser regressão.

**Mitigação:**
- Gerar uma edição via engine e a mesma edição via Claude artesanal em paralelo
- Comparar lado a lado com a Juliana
- Iterar em pontos divergentes (5-10 ciclos esperados)
- Só "graduar" a engine quando ela atingir 90%+ de paridade visual com o que a Juliana aprovaria

### Risco 2: equipe esquece de preencher campo crítico

A engine para com mensagem clara, mas se isso acontece todo mês vira atrito.

**Mitigação:**
- Validador roda diariamente nos pacotes em produção do mês — alerta antes do dia da geração
- Sheet de Config tem **células coloridas** (formatação condicional) — vermelho se vazio em campo crítico
- Template inicial vem totalmente preenchido com exemplos, equipe só ajusta valores

### Risco 3: tema visual da revista evolui — engine fica desatualizada

A revista é viva, vocês ajustam visual a cada poucas edições.

**Mitigação:**
- Tema fica em arquivo separado (`tema.yaml` + folha de estilos referenciada)
- Mudanças visuais não exigem mexer em código da engine
- Ajustes de identidade visual ficam num PR pequeno e isolado

---

## Sinal verde para começar a codar

Antes de eu começar a implementação real, três confirmações finais da Juliana:

1. **A hierarquia `Mês > Condomínio > _Editorial Mensal` faz sentido?** A `_Editorial Mensal/` dentro de cada mês é nova — preciso criá-la.

2. **Estratégia de não-migração retroativa funciona?** Edições antigas ficam como estão; só edições novas vão pra estrutura final.

3. **Sheets como formato padrão para Config + Editorial?** Vocês toparam Sheets, mas vale confirmar que isso vale tanto pro Editorial Mensal quanto pro Config de cada condomínio.

Com esses três OK, o próximo passo é eu **criar a `_Editorial Mensal/` da edição 05/2026 vazia no Drive** como pasta-modelo, e começar a implementar o `FlatFolderReader` para a engine ler a pasta atual do Gardens.
