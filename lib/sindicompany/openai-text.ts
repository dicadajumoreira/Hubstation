/**
 * Cliente leve da OpenAI Chat Completions API pra geração de copy
 * de carrossel Instagram. Sem dependência externa — fetch direto.
 */

import type { CarrosselCopy, CarrosselSlide } from "./carrosseis";
import { getMarca, listMarcas } from "./marcas-db";

const OPENAI_API = "https://api.openai.com/v1/chat/completions";

/** Instruções detalhadas por formato de carrossel. Só o bloco do
 *  formato escolhido é injetado no prompt — mantém o prompt enxuto. */
const FORMATO_INSTRUCOES: Record<string, string> = {
  historia_real:
    `FORMATO: HISTÓRIA REAL (o que mais engaja e salva).\n` +
    `- Dê um NOME PRÓPRIO ao personagem (use o nome indicado abaixo no briefing), nunca "um morador".\n` +
    `- Detalhes concretos tornam crível: "6 kg", "4 horas", "23%". NUNCA cite número de apartamento/unidade.\n` +
    `- A história tem virada: setup → conflito → descoberta → resolução.\n` +
    `- Personagens/situações podem ser compostos. NUNCA cite nome de condomínio (real ou inventado), endereço, nem número de unidade/apartamento.\n` +
    `ESTRUTURA DE SLIDES:\n` +
    `  1 (capa): hook — o momento de tensão máxima, sem resolver. + tarja FORMATO.\n` +
    `  2: quem é o personagem e qual o problema.\n` +
    `  3: o erro que quase aconteceu (ou aconteceu).\n` +
    `  4: a virada — o que descobriu/aprendeu/fez.\n` +
    `  5: o resultado concreto (com número).\n` +
    `  último: CTA "Você já passou por isso? Comenta SIM ou NÃO".`,
  lista:
    `FORMATO: LISTA (educativo, pontos equivalentes).\n` +
    `- MÁXIMO 5 itens. Cada item cabe em UMA linha — se não couber, está longo demais.\n` +
    `- Ordene do MENOS óbvio pro MAIS surpreendente: o item 5 precisa chocar.\n` +
    `- Os números são parte do design (Black 900, mint, grande) — o body do slide só explica curto.\n` +
    `- Sem bullet points no texto. A lista vive nos slides numerados.\n` +
    `ESTRUTURA DE SLIDES:\n` +
    `  1 (capa): "X coisas que [ação provocativa]". + tarja FORMATO.\n` +
    `  2 a N-1: um item por slide — número no título + explicação curta no body.\n` +
    `  último: CTA "Qual você não sabia? Comenta o número aqui".`,
  mito_verdade:
    `FORMATO: MITO VS VERDADE (crenças erradas difundidas).\n` +
    `- Sempre em PARES: Mito num slide, Verdade no slide seguinte.\n` +
    `- O mito precisa SOAR RAZOÁVEL — senão não tem impacto desmistificar.\n` +
    `- A verdade precisa ser ESPECÍFICA: "a lei diz exatamente o oposto", não "não é bem assim". Cite artigo/REsp quando der.\n` +
    `- MÁXIMO 3 pares por carrossel.\n` +
    `ESTRUTURA DE SLIDES:\n` +
    `  1 (capa): "Você acredita em algum desses mitos sobre condomínio?". + tarja FORMATO.\n` +
    `  2,3: Mito 1 → Verdade 1.  4,5: Mito 2 → Verdade 2.  (e assim por diante até 3 pares)\n` +
    `  No tipo de cada slide: use "mito" pros slides de mito e "verdade" pros de verdade.\n` +
    `  último: CTA "Qual mito você acreditava? Comenta aqui".`,
  antes_depois:
    `FORMATO: ANTES / DEPOIS (resultado tangível de gestão profissional).\n` +
    `- O "depois" precisa ter NÚMERO concreto: "caiu de 23% pra 4% em 6 meses", não "melhorou muito".\n` +
    `- O "antes" precisa ser RECONHECÍVEL: o leitor pensa "isso parece o meu prédio".\n` +
    `- NUNCA fabricar resultados. Se não tem dado plausível, use outro ângulo dentro do formato.\n` +
    `ESTRUTURA DE SLIDES:\n` +
    `  1 (capa): o dado do "depois" em destaque — o resultado final primeiro. + tarja FORMATO.\n` +
    `  2: o "antes" — como estava o condomínio.\n` +
    `  3: o problema raiz — por que estava assim.\n` +
    `  4: o que mudou — decisão/ação que virou o jogo.\n` +
    `  5: o "depois" detalhado com todos os números.\n` +
    `  último: CTA "Seu condomínio está no antes ou no depois?".`,
  dado_choca:
    `FORMATO: DADO QUE CHOCA (estatística surpreendente com fonte).\n` +
    `- Use só dados que você conhece com FONTE IDENTIFICÁVEL (SíndicoNet, IBGE, SECOVI, STJ, leis federais, reportagens datadas). NUNCA invente números. NUNCA "estudos mostram" ou "especialistas afirmam".\n` +
    `- Reescreva o dado com suas palavras (fato é livre, texto da fonte não).\n` +
    `- Cite a fonte no slide E na legenda: "Fonte: SíndicoNet, 2025" (formato mínimo). Se não souber um dado real e atual, prefira uma referência legal sólida (ex: Lei 4.591/64, Código Civil art. 1.336) reescrita como dado.\n` +
    `ESTRUTURA DE SLIDES:\n` +
    `  1 (capa): SÓ o número em destaque, sem contexto ainda — número Black 900, mint/sand, ocupa o slide. + tarja FORMATO.\n` +
    `  2: o que esse número significa na vida real do morador.\n` +
    `  3: quem está dentro do dado — a pessoa por trás da estatística.\n` +
    `  4: o contraponto — o que muda quando se sabe o dado.\n` +
    `  5: o que fazer com essa informação.\n` +
    `  último: CTA "Você está nesse número? Comenta SIM ou NÃO".`,
  tutorial:
    `FORMATO: TUTORIAL RÁPIDO (ação prática que dá pra fazer hoje).\n` +
    `- MÁXIMO 5 passos. Cada passo COMEÇA com verbo de ação: "Solicite", "Anote", "Envie", "Guarde", "Exija".\n` +
    `- Sem jargão jurídico sem tradução imediata. Citou lei? Explique em uma frase o que significa.\n` +
    `- Precisa ser acionável HOJE. Se depende de advogado/processo, não é tutorial.\n` +
    `- O ÚLTIMO slide tem um modelo de texto/script que o morador copia direto.\n` +
    `ESTRUTURA DE SLIDES:\n` +
    `  1 (capa): o problema que o tutorial resolve, em forma de pergunta. + tarja FORMATO.\n` +
    `  2: por que a maioria não faz — a barreira que o tutorial derruba.\n` +
    `  3 a N-1: um passo por slide, numerado, verbo de ação no início.\n` +
    `  último: o modelo/script copiável + CTA "Salva esse post. Você vai precisar.".`,
  opiniao:
    `FORMATO: OPINIÃO FORTE (posição clara da MARCA sobre tema polêmico).\n` +
    `- A opinião é da MARCA (perfil da conta), não de personagem fictício.\n` +
    `- Precisa de ARGUMENTO: 2-3 razões concretas que sustentam a posição.\n` +
    `- ANTECIPE o contra-argumento num slide ("eu sei que você discorda, mas...") + responda.\n` +
    `- NUNCA atacar pessoas — a opinião é sobre prática/sistema, nunca sobre síndicos/moradores/gestoras específicas.\n` +
    `- CTA obrigatoriamente de DEBATE: dois lados claros.\n` +
    `ESTRUTURA DE SLIDES:\n` +
    `  1 (capa): a afirmação provocativa sem contexto — MÁXIMO 6 palavras. + tarja FORMATO.\n` +
    `  2: o problema que motivou a opinião — dado ou situação real.\n` +
    `  3: argumento 1 — a razão principal.\n` +
    `  4: o contra-argumento que o leitor vai pensar — e a resposta a ele.\n` +
    `  5: argumento 2 e consequência prática.\n` +
    `  último: CTA "Concorda ou discorda? Comenta CONCORDO ou DISCORDO.".`,
  hook_punch:
    `FORMATO: HOOK PUNCH (o mais agressivo — para o scroll na hora).\n` +
    `- Frases CURTAS e fortes, poucas palavras por slide, ritmo rápido, tensão alta. Cada slide é um soco.\n` +
    `- Nada de explicação longa: impacto emocional progressivo, um golpe por slide.\n` +
    `- Use bastante verdade humana e palavras magnéticas. Vários slides funcionam como respiro (tipo "frase").\n` +
    `- Capa: a frase mais forte possível, máx 6 palavras.`,
  pov:
    `FORMATO: POV (point of view — identificação extrema, "isso sou eu").\n` +
    `- Capa começa com "POV:" + uma situação MUITO específica e reconhecível (ex: "POV: você abriu o grupo do condomínio às 22h.").\n` +
    `- Tom cinematográfico, presente, em 2a pessoa ("você..."). Escalada emocional até uma verdade humana.\n` +
    `- O objetivo é o leitor pensar "sou eu / é alguém que conheço" e marcar/compartilhar.\n` +
    `- CTA de identificação ou compartilhamento.`,
  tweet:
    `FORMATO: TWEET STYLE (frase curta, printável, repostável).\n` +
    `- Cada slide é uma frase de efeito que funciona SOZINHA — observação humana, verdade incômoda ou indireta. Leitura instantânea.\n` +
    `- Quase todos os slides são tipo "frase" (limpo, centralizado). Nada de parágrafo.\n` +
    `- Pensado pra print/repost e branding. Máx 1 ideia por slide.\n` +
    `- CTA leve de compartilhamento.`,
  expectativa_realidade:
    `FORMATO: EXPECTATIVA VS REALIDADE (humor + identificação).\n` +
    `- Capa apresenta a EXPECTATIVA idealizada; os slides seguintes mostram a REALIDADE absurda/caótica, com humor leve.\n` +
    `- Contraste forte e identificável entre o que se imagina e o que acontece de verdade. Ótimo pra meme/compartilhamento.\n` +
    `- Fechamento com reflexão leve. CTA de compartilhamento/marcação.`,
  erro_fatal:
    `FORMATO: ERRO FATAL (medo de errar).\n` +
    `- Capa nomeia O erro que custa caro (ex: "O erro que destrói assembleias."). \n` +
    `- Mostra a consequência, AMPLIFICA o prejuízo/risco, depois entrega a solução prática.\n` +
    `- Ativa culpa/medo de prejuízo + utilidade. CTA de salvamento.`,
  bastidor:
    `FORMATO: BASTIDOR REAL (documental, humaniza).\n` +
    `- Mostra o bastidor real de uma situação (visita técnica, reunião difícil, vistoria) + um DETALHE INVISÍVEL que só quem vive percebe.\n` +
    `- Sensação real e próxima, percepção premium. Tom de quem está dentro, não de quem ensina de fora.\n` +
    `- Termina em reflexão/frase forte. CTA de identificação ou autoridade.`,
  camada_invisivel:
    `FORMATO: CAMADA INVISÍVEL (profundidade emocional).\n` +
    `- Parte de uma situação comum e revela a CAMADA emocional escondida por trás dela (ex: "muita reclamação nasce do cansaço").\n` +
    `- Provoca o "nunca pensei nisso". Verdade humana forte + frase memorável. Altamente compartilhável.\n` +
    `- CTA emocional / de compartilhamento.`,
  dialogo:
    `FORMATO: DIÁLOGO (conversa).\n` +
    `- Troca curta de falas entre dois personagens, com os falantes nomeados no início de cada fala (ex: body "Morador: Mas é rapidinho." / próximo slide body "Síndico: Todo problema começa com rapidinho.").\n` +
    `- Escalada emocional e um PUNCH na última fala. Leitura rápida, humana, ótima pra print.\n` +
    `- NÃO usar nome de condomínio nem nº de unidade. CTA de identificação.`,
  desabafo:
    `FORMATO: DESABAFO CONTROLADO (emocional, íntimo).\n` +
    `- Mostra a dor/pressão real de quem gere — vulnerabilidade CONTROLADA, sem vitimismo nem drama.\n` +
    `- Tom íntimo, humano, de quem entende por dentro; cria comunidade e pertencimento (ex: "Tem dia que o síndico só queria desligar o celular.").\n` +
    `- Termina em reflexão/frase forte. CTA emocional ou de identificação.`,
  escalada:
    `FORMATO: A ESCALADA (tensão crescente, cinematográfica).\n` +
    `- Começa numa situação simples e PIORA a cada slide (caos crescente) até um pico emocional, depois uma reflexão final.\n` +
    `- Cada slide eleva a tensão do anterior — ritmo forte que prende até o fim (ex: comunicado ignorado → conflito → grupo explode → assembleia vira guerra).\n` +
    `- Use micro-tensão entre os slides. CTA de debate ou identificação.`,
};

interface ChatOk {
  ok: true;
  content: string;
}
interface ChatErr {
  ok: false;
  error: string;
}

// ---------------------------------------------------------------------------
// System prompts. A PERSONA de cada marca (voz, publico, tom, o que viraliza)
// agora vive na tabela `marcas` (coluna persona) — leia via getMarca(slug).
// As constantes abaixo sao genericas: fallback pra marca sem persona e o
// system prompt das tarefas de TRADUCAO (que nao precisam de voz de marca).
// ---------------------------------------------------------------------------
const SYSTEM_FALLBACK =
  "Você é redator de carrosséis de Instagram. Português brasileiro com " +
  "TODOS os acentos corretos. Voz humana, frases curtas e diretas, sem " +
  "linguagem corporativa vazia. Use apenas aspas retas (\").";

const TRANSLATOR_SYSTEM =
  "Você é um tradutor técnico português→inglês para prompts de geração de " +
  "imagem. Responda apenas com o JSON pedido, sem comentários.";

async function chat(
  prompt: string,
  systemPrompt: string = SYSTEM_FALLBACK,
): Promise<ChatOk | ChatErr> {
  const apiKey = (process.env.OPENAI_API_KEY ?? "").trim().replace(/^Bearer\s+/i, "");
  if (!apiKey || !apiKey.startsWith("sk-")) {
    return { ok: false, error: "OPENAI_API_KEY ausente ou inválida." };
  }
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${apiKey}`,
  };
  const orgId = (process.env.OPENAI_ORGANIZATION ?? "").trim();
  if (orgId) headers["OpenAI-Organization"] = orgId;
  const projId = (process.env.OPENAI_PROJECT ?? "").trim();
  if (projId) headers["OpenAI-Project"] = projId;

  let res: Response;
  try {
    res = await fetch(OPENAI_API, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: process.env.OPENAI_MODEL ?? "gpt-4o-mini",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: prompt },
        ],
        temperature: 0.85,
        max_tokens: 2000,
        response_format: { type: "json_object" },
      }),
    });
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? `Falha de rede: ${e.message}` : "Falha de rede.",
    };
  }

  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json())?.error?.message ?? "";
    } catch {
      detail = await res.text().catch(() => "");
    }
    return { ok: false, error: `OpenAI ${res.status}: ${detail.slice(0, 160)}` };
  }

  let data: { choices?: Array<{ message?: { content?: string } }> };
  try {
    data = await res.json();
  } catch {
    return { ok: false, error: "OpenAI retornou JSON inválido." };
  }
  const content = data.choices?.[0]?.message?.content?.trim();
  if (!content) return { ok: false, error: "OpenAI retornou resposta vazia." };
  return { ok: true, content };
}

// PASSO 0 — objetivo do carrossel. GLOBAL pra todas as marcas: define o
// que o post precisa provocar (tom, gancho, CTA, criterio de sucesso).
// A VOZ de cada marca vem da persona (tabela marcas), nao daqui. Um
// carrossel = UMA intencao principal.
const OBJETIVO_INSTRUCOES: Record<string, string> = {
  comentarios:
    `OBJETIVO: GERAR COMENTÁRIOS (DEBATE).\n` +
    `- O carrossel PRECISA dividir opiniões com dois lados reconhecíveis. Sucesso = discussão nos comentários, não alcance.\n` +
    `- CTA que gera DEBATE, coerente com a emoção do post — opinião forte, posicionamento ou dilema (ex: "Isso é convivência ou abuso?", "Até onde vai o limite?", "O problema começa em quem?", "Síndico precisa ser firme ou flexível?"). Binário "SIM ou NÃO" só quando a discussão for REALMENTE binária — não repita sempre. NUNCA "o que você acha?"/"comenta aqui" (aberto demais reduz comentários).\n` +
    `- O tema precisa ter DOIS lados defensáveis. Sem conflito legítimo não há debate.\n` +
    `- O ÚLTIMO SLIDE nomeia explicitamente os dois lados — o leitor precisa saber exatamente o que comentar.`,
  salvamentos:
    `OBJETIVO: GERAR SALVAMENTOS (UTILIDADE).\n` +
    `- O post precisa ser tão útil que o leitor queira guardar pra consultar depois. Sucesso = salvamentos, compartilhamentos, envio em grupos. Comentários NÃO são prioridade.\n` +
    `- Linguagem objetiva, confiável, menos emocional — percepção de "referência".\n` +
    `- SEMPRE que possível ancore: lei, artigo, norma, número, regra prática. Destaque visual pra artigos, números e exceções.\n` +
    `- CTA foca em SALVAR ("Salva esse post.", "Manda no grupo."). NUNCA CTA de debate.`,
  clientes:
    `OBJETIVO: ATRAIR NOVOS CLIENTES.\n` +
    `- O público-alvo precisa perceber que vive um problema que a marca resolve. Sucesso = DMs, leads, cliques no link da bio.\n` +
    `- NUNCA venda diretamente. Mostre a dor, o "antes" e o resultado final com NÚMEROS reais (economia, prazo, redução de problema). Específico converte mais que promessa genérica.\n` +
    `- A marca PODE aparecer mais e a assinatura pode entrar no fechamento.\n` +
    `- CTA leve, nunca anúncio direto (ex: "A gente resolve.", "Fala com a gente.", "Link na bio.").`,
  autoridade:
    `OBJETIVO: POSICIONAR AUTORIDADE NO MERCADO.\n` +
    `- Eleva a marca como REFERÊNCIA no seu nicho. Não é vender agora — é fazer o mercado perceber que a marca opera num outro nível. Sucesso = compartilhamentos qualificados, percepção de elite.\n` +
    `- Linguagem sofisticada, estratégica, menos emocional. Visão de mercado, tendência, profissionalização do setor.\n` +
    `- CTA institucional e elegante (ex: "O mercado mudou.", "Os que entenderem isso primeiro saem na frente.").\n` +
    `- Formatos fortes aqui: Manifesto, tendência, dado que choca, visão estratégica.`,
  educar:
    `OBJETIVO: EDUCAR O PÚBLICO.\n` +
    `- Ensinar algo que o público não sabe mas deveria. Gatilho: SURPRESA + IDENTIFICAÇÃO. A surpresa importa mais que a aula.\n` +
    `- Linguagem MUITO acessível. Sem juridiquês, sem tom professoral. Preferir "a maioria não sabe, mas...", "isso quase ninguém te explica".\n` +
    `- Estrutura: primeiro o problema que o público já conhece; depois o que ele não sabia. Uma ideia por slide.\n` +
    `- CTA depende do tema: muito útil → "Salva esse post"; divide opiniões → CTA binário.`,
};

// Esqueleto emocional por quantidade de slides (estrutura ideal). O modelo
// segue este arco e encaixa o FORMATO/tema dentro. RESPIRO = slide tipo
// "frase" (limpo, centralizado). Último slide = sempre CTA.
const ESTRUTURA_POR_SLIDES: Record<number, string> = {
  5: '1 Hook · 2 Amplificação da dor/conflito · 3 Virada/verdade incômoda · 4 Solução/posicionamento · 5 Frase memorável + CTA',
  6: '1 Hook · 2 Identificação · 3 Amplificação da dor · 4 Verdade incômoda/virada · 5 Solução/visão · 6 Frase memorável + CTA',
  7: '1 Hook · 2 Contexto/cena · 3 Problema principal · 4 Micro-tensão (abre loop) · 5 Verdade humana · 6 Solução/posicionamento · 7 Frase final + CTA',
  8: '1 Hook · 2 Identificação · 3 Amplificação do caos/dor · 4 Verdade incômoda · 5 RESPIRO (tipo "frase") · 6 Explicação/solução · 7 Frase memorável · 8 CTA',
  9: '1 Hook · 2 Contexto · 3 Identificação · 4 Amplificação da dor · 5 Micro-tensão · 6 Verdade humana · 7 Solução/posicionamento · 8 Frase memorável · 9 CTA',
  10: '1 Hook · 2 Contexto/personagem · 3 Identificação · 4 Amplificação do problema · 5 Micro-tensão · 6 Verdade incômoda · 7 RESPIRO (tipo "frase") · 8 Solução/nova visão · 9 Frase memorável (manifesto) · 10 CTA',
};

// Pool de nomes pra personagens de HISTÓRIA REAL. Um nome aleatório é
// injetado por geração pra evitar que o modelo ancore sempre no mesmo
// (cada chamada da API é stateless, então sem isso ele repete o primeiro
// exemplo do prompt em todo roteiro).
const NOMES_PERSONAGEM = [
  "Marina", "Rafael", "Camila", "Bruno", "Patrícia", "Thiago", "Juliana",
  "Eduardo", "Fernanda", "Gustavo", "Letícia", "Rodrigo", "Aline", "Felipe",
  "Carla", "Diego", "Vanessa", "André", "Beatriz", "Marcelo", "Sabrina",
  "Leonardo", "Priscila", "Vinícius", "Tatiane", "Henrique", "Larissa",
  "Fábio", "Daniela", "Otávio", "Mariana", "Ricardo", "Cláudia", "Renato",
];

/** Gera 3 versões de copy pra carrossel — angulos editoriais distintos.
 *  O `brand` muda a estrategia (publico, objetivo, linguagem, assinatura).
 *  O `objetivo` define tom/gancho/CTA/formato/sucesso (mapas distintos
 *  por marca: morador vs sindico profissional). */
export async function gerarTresCopies(input: {
  brand?: string;
  objetivo?: string;
  titulo: string;
  tema: string;
  formato: string;
  n_slides: number;
  briefing?: string;
}): Promise<{ ok: true; copies: CarrosselCopy[] } | { ok: false; error: string }> {
  const brand = input.brand || "sindicompanybr";
  // Persona, handle e assinatura vem da tabela marcas. A persona (guia
  // da marca) e o system prompt — carrega TODA a voz/estrategia/contexto;
  // os blocos hardcoded por marca foram aposentados em favor dela.
  const marca = await getMarca(brand);
  const systemPrompt = marca?.persona || SYSTEM_FALLBACK;
  const handle = marca?.handle || `@${brand}`;
  const assinatura = marca?.assinatura || "";

  const objetivoBloco =
    input.objetivo && OBJETIVO_INSTRUCOES[input.objetivo]
      ? `\n${OBJETIVO_INSTRUCOES[input.objetivo]}\n`
      : "";
  const formato_label = input.formato.replaceAll("_", " ");
  const instrucoesFormato =
    FORMATO_INSTRUCOES[input.formato] ??
    `FORMATO: ${formato_label} (estrutura livre, mantendo a voz da marca).`;

  // anti-leak generico: nao citar nenhuma OUTRA marca cadastrada (nome
  // ou handle). Substitui a regra antes hardcoded so pra Consvicta.
  const concorrentes = (await listMarcas({ ativo: true }))
    .filter((m) => m.slug !== brand)
    .flatMap((m) => [m.nome, m.handle])
    .filter(Boolean);
  const antiLeak =
    concorrentes.length > 0
      ? `- PROIBIDO mencionar outras marcas/concorrentes (${concorrentes.join(", ")}) nos slides ou na legenda. Só ${marca?.nome ?? handle} aparece, e a única assinatura é "${assinatura}".\n`
      : "";

  // 3 angulos editoriais GENERICOS pras 3 versoes — a persona refina o
  // tom de cada um conforme a marca.
  const angulos = [
    "Recorte 1: o ângulo mais humano/emocional do tema — identificação, dor real, bastidor.",
    "Recorte 2: o ângulo de processo/governança/dados — o lado técnico e organizacional.",
    "Recorte 3: o ângulo da transformação — o que muda quando a gestão é profissional.",
  ];

  const buildPrompt = (angulo: string): string => {
    const nomePersonagem =
      NOMES_PERSONAGEM[Math.floor(Math.random() * NOMES_PERSONAGEM.length)];
    const nomeDirective =
      input.formato === "historia_real"
        ? `- PERSONAGEM: neste roteiro o protagonista se chama ${nomePersonagem}. Varie os nomes dos personagens secundários e nunca repita sempre o mesmo nome.\n`
        : "";
    return (
    `Crie UMA versão de copy pra um carrossel do ${handle}.\n` +
    `A VOZ, o público, o tom e o que pode/não pode estão no system prompt (a persona da marca) — SIGA À RISCA.\n` +
    objetivoBloco +
    `\nBRIEFING:\n` +
    `- Título interno: ${input.titulo}\n` +
    `- Tema: ${input.tema}\n` +
    `- Formato: ${formato_label}\n` +
    `- Quantidade de slides: ${input.n_slides}\n` +
    (input.briefing ? `- Contexto extra: ${input.briefing}\n` : "") +
    `- ${angulo}\n` +
    `\n${instrucoesFormato}\n` +
    nomeDirective +
    `\n` +
    (objetivoBloco
      ? `IMPORTANTE: o OBJETIVO acima é a intenção PRINCIPAL — quando objetivo e formato divergirem, o objetivo manda (CTA, tom, estrutura).\n\n`
      : "") +
    `VOZ: siga a persona da marca (system prompt) — tom, público, o que viraliza, o que nunca fazer. A ASSINATURA "${assinatura}" aparece SÓ na legenda, nunca nos slides.\n` +
    `ESTRUTURA: use o FORMATO acima e EXATAMENTE ${input.n_slides} slides. Se a persona sugerir outra contagem/estrutura, o FORMATO e a quantidade de slides deste post MANDAM.\n\n` +
    `REGRAS:\n` +
    `- Capa: o tema "${input.tema}" aparece literal ou em paráfrase clara. Capa inteira (titulo + body) tem no máximo 20 palavras.\n` +
    `- HOOK DA CAPA (prioridade máxima): o título da capa é a frase que PARA O SCROLL — verdade incômoda, identificação, tensão ou curiosidade. Curto, leitura instantânea no celular. NUNCA slogan corporativo, frase genérica ou que começa devagar; deve funcionar sozinho, sem depender de contexto.\n` +
    `- DESTAQUE DO HOOK: envolva o trecho MAIS FORTE do hook (2 a 5 palavras) entre [[ ]] — ex: "WhatsApp [[não é assembleia]].", "O síndico cansado começa a [[perder autoridade]].". Marque [[ ]] APENAS no título da capa (slide 1), nunca nos outros slides nem na legenda.\n` +
    `- ÂNCORAS DE ATENÇÃO (retenção): nos slides de conteúdo, marque com [[ ]] dentro do BODY no máximo 1 trecho de alto impacto por slide (no máximo +1 secundário) — verdade incômoda, identificação, tensão, frase memorável OU uma PALAVRA MAGNÉTICA: caos, silêncio, pressão, desgaste, autoridade, conflito, refém, invisível, bastidor, premium, processo, improviso, abandono, controle, presença, sobrecarga, suporte, confiança, clareza, método, crise. NUNCA mais de 2 por slide; destacar demais tira a força.\n` +
    `- CTA (último slide): marque a ação entre [[ ]] e faça-a CONTINUAÇÃO natural da emoção construída, nunca "curta e siga". Escolha o tipo pela emoção do post: indignação → opinião forte/dilema; identificação → experiência pessoal ("Qual situação parecida você já viveu?"); tensão → debate; aprendizado → salvar ("[[Salva]] pra próxima assembleia."); indireta → compartilhar ("[[Manda no grupo]] de quem precisa ouvir."); desejo → aspiracional ("Gestão premium começa nos [[detalhes]]."). EVITE repetir "SIM ou NÃO", "Concorda?", "O que acha?" — binário só quando a discussão for de fato binária. O CTA é parte do roteiro emocional, não um detalhe final.\n` +
    `- ESTRUTURA (siga este esqueleto emocional, encaixando o FORMATO/tema dentro): ${ESTRUTURA_POR_SLIDES[input.n_slides] ?? "Hook → dor → verdade incômoda → solução → frase memorável + CTA"}. Slides marcados RESPIRO usam tipo "frase" (slide limpo/centralizado). Alterne o tom (tensão, identificação, reflexão) — nunca o mesmo por vários slides. Use um MINI PLOT TWIST quando couber ("parecia X. Nunca foi sobre X. Era sobre Y.").\n` +
    `- VOZ HUMANA: frases faláveis, ritmo oral, pausas naturais — sem juridiquês, academiquês nem excesso de conectivos. EFEITO ESPELHO: ao menos 1 frase que faça pensar "isso sou eu" ou "isso é alguém que conheço". AUTORIDADE INVISÍVEL: nunca dizer "somos referência/especialistas"; a autoridade aparece na clareza e na observação humana.\n` +
    `- Cada slide interno: tipo + título (3-7 palavras) + body (1-3 frases curtas, máx 35 palavras). Seja conciso — não encha linguiça.\n` +
    `- MICRO-TENSÃO (retenção entre slides): os slides do MEIO devem terminar com um gancho que puxa o próximo — curiosidade, tensão ou continuação emocional —, nunca 100% fechados. O usuário tem que pensar "deixa eu ver o próximo". Marque a frase de tensão/cliffhanger entre ~~ ~~ (vira SUBLINHADO, distinto do grifo do [[ ]]) — ex: "~~Mas o problema começa depois.~~", "~~E é aqui que a gestão perde autoridade.~~". Evite explicação técnica contínua e slides conclusivos no meio. Só o ÚLTIMO slide (CTA) e a frase final memorável podem fechar.\n` +
    `- VERDADE HUMANA (o que MAIS viraliza): condomínio é comportamento humano. Prefira observações reais da vida que façam pensar "isso é MUITO verdade" a explicação técnica. Ex: "O problema raramente começa no problema.", "Síndico forte também cansa.", "O grupo do WhatsApp muda o comportamento das pessoas.", "A maioria quer convivência. Até ser contrariada.".\n` +
    `- FRASE PRINTÁVEL + INDIRETA SOCIAL: inclua pelo menos 1 frase digna de print/repost — forte, memorável, compartilhável (ex: "Condomínio não funciona no grito. Funciona no processo.", "Fornecedor bom aparece no suporte."). Vale a INDIRETA (parece reflexão, é indireta): "Tem morador que quer regra. Até a regra chegar nele." — gera marcação e compartilhamento em grupo.\n` +
    `- RESPIRO VISUAL (ritmo): alterne slides densos e leves; NUNCA todos com a mesma densidade. Inclua pelo menos 1 slide com tipo "frase": SÓ uma frase curta, forte e memorável (a printável/verdade humana), com body vazio — ele vai num layout limpo e centralizado.\n` +
    `- SENSAÇÃO EDITORIAL: o carrossel deve parecer revista/manifesto, não post de marketing genérico. Menos texto, mais peso. Não encha de elementos nem de jargão.\n` +
    `- NUNCA cite número de apartamento/unidade nem nome de condomínio (real ou inventado) em nenhum slide ou legenda. Personagem e situação ficam sem identificar prédio ou unidade.\n` +
    `- Em posts educativos (mito, dado, tutorial, lista jurídica): pelo menos UMA âncora — artigo (ex: "Código Civil, art. 1.336"), decisão judicial (ex: "STJ, REsp 1.699.022/SP, 2019") OU dado com fonte nomeada e datada.\n` +
    antiLeak +
    `- LEGENDA Instagram: 4-8 linhas, hook na primeira, termina OBRIGATORIAMENTE com "${assinatura}" e EXATAMENTE 3 hashtags na linha seguinte (uma da marca + 2 do tema).\n` +
    `- Acentos corretos em TODA palavra (você, síndico, condomínio, gestão). NUNCA: gerúndio, travessão (—), aspas curvas, emoji decorativo no slide, frases de introdução ("é importante ressaltar").\n` +
    `- LISTA NEGRA: papel fundamental, momento crucial, cenário em constante evolução, destacando a importância, o futuro é promissor, juntos somos mais fortes, destaca-se, vibrante, no coração de, em meio a, reflete a, simboliza a, evidencia a, desafios e oportunidades, rica diversidade, não apenas X mas também Y, mergulhando em, celebrando a, fomentando o, estudos mostram, especialistas afirmam.\n\n` +
    `Devolva JSON estrito (sem markdown):\n` +
    `{ "slides": [{"tipo":"capa","titulo":"...","body":"..."}, ... total ${input.n_slides} slides], "legenda":"..." }`
    );
  };

  // 3 chamadas em PARALELO, uma por angulo — cada uma e pequena (~6 slides
  // + legenda), entao termina rapido e cabe folgado no cap de 26s do
  // Netlify. Antes era uma chamada unica gerando as 3 versoes, que
  // estourava o tempo limite com o prompt grande.
  let results: ({ ok: true; content: string } | { ok: false; error: string })[];
  try {
    results = await Promise.all(angulos.map((a) => chat(buildPrompt(a), systemPrompt)));
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Falha de rede ao gerar copy.",
    };
  }

  const copiesRaw: CarrosselCopy[] = [];
  let lastErr = "";
  for (const r of results) {
    if (!r.ok) {
      lastErr = r.error;
      continue;
    }
    try {
      const parsed = JSON.parse(r.content) as Partial<CarrosselCopy>;
      if (Array.isArray(parsed.slides) && parsed.slides.length > 0) {
        copiesRaw.push({
          slides: parsed.slides as CarrosselSlide[],
          legenda: typeof parsed.legenda === "string" ? parsed.legenda : "",
        });
      }
    } catch {
      lastErr = "Resposta da IA não é JSON válido.";
    }
  }
  if (copiesRaw.length === 0) {
    return { ok: false, error: lastErr || "IA não retornou nenhuma opção de copy." };
  }
  const normalized: CarrosselCopy[] = copiesRaw.map((o) => {
    const slides = (o.slides ?? []).slice(0, input.n_slides);
    while (slides.length < input.n_slides) {
      slides.push({ tipo: "texto", titulo: "", body: "" });
    }
    return { slides, legenda: o.legenda ?? "" };
  });
  return { ok: true, copies: normalized };
}

/** Traduz fielmente a descricao livre que a editora escreveu na
 *  textarea 'Descrever a imagem'. Diferente de descreverCenaParaCapa,
 *  NAO inventa cena nem reduz detalhes — preserva pessoas, ambientes,
 *  objetos, cores, climas que ela mencionou. So neutraliza palavras
 *  que DALL-E bloqueia (violencia, armas, drogas, marcas comerciais).
 *  Se nada precisar mudar, devolve traducao literal. */
export async function traduzirDescricaoUsuario(
  descPt: string,
): Promise<{ ok: true; descEn: string } | { ok: false; error: string }> {
  const prompt =
    `Translate this Brazilian Portuguese photo description into English ` +
    `for a DALL-E prompt. Rules:\n` +
    `- Preserve EVERY visual detail the author wrote: people, age, ` +
    `clothing, gender, environment, objects, colors, time of day, mood.\n` +
    `- Do NOT add scenes or details the author did not mention.\n` +
    `- Do NOT remove details (do not 'simplify').\n` +
    `- Sanitize words that DALL-E commonly blocks: replace ` +
    `weapons/violence/drugs/crime/illegal acts with neutral equivalents; ` +
    `replace specific real-person names (politicians, celebrities) with ` +
    `'a person'; replace specific brand names ('Apple iPhone' -> ` +
    `'a smartphone'); replace 'briga'/'conflito' with 'conversation' or ` +
    `'meeting'; replace 'inadimplencia'/'divida' with 'paperwork' or ` +
    `'documents'; replace 'seguranca'/'security guard' with 'concierge' ` +
    `or 'doorman'.\n` +
    `- Output: a single English sentence/paragraph faithful to the original. ` +
    `No quotes, no commentary.\n` +
    `- Output JSON: {"desc_en": "..."}\n\n` +
    `INPUT:\n${descPt}`;

  const r = await chat(prompt, TRANSLATOR_SYSTEM);
  if (!r.ok) return { ok: false, error: r.error };
  let parsed: { desc_en?: string };
  try {
    parsed = JSON.parse(r.content);
  } catch {
    return { ok: false, error: "Traducao do prompt: JSON invalido." };
  }
  const desc = (parsed.desc_en ?? "").trim();
  if (!desc) return { ok: false, error: "Traducao vazia." };
  return { ok: true, descEn: desc };
}

/** Pega a copy escolhida (em pt-BR, podendo conter palavras "sensíveis"
 *  como conflito/inadimplência) e devolve UMA frase em inglês, neutra,
 *  100% visual/fotográfica, pronta pra alimentar o DALL-E sem disparar
 *  os filtros de safety. */
export async function descreverCenaParaCapa(input: {
  tema: string | null;
  tituloCapa: string;
  subtitulo: string;
}): Promise<{ ok: true; sceneEn: string } | { ok: false; error: string }> {
  const prompt =
    `Convert this Brazilian Instagram carousel cover into a single English ` +
    `sentence describing a concrete photographable SCENE for a documentary ` +
    `editorial photo. Rules:\n` +
    `- One sentence, max 35 words.\n` +
    `- Concrete visible objects/setting only (lobby, garden, hallway, ` +
    `balcony, kitchen, common area, plants, daylight, etc).\n` +
    `- No abstract concepts (no "security", "conflict", "justice", ` +
    `"crisis", "debt", "violence"). Translate any negative theme into a ` +
    `neutral everyday scene about Brazilian condominium life.\n` +
    `- People (if any): adults in everyday clothes, calm body language, ` +
    `no weapons, no fighting, no medical emergencies.\n` +
    `- No brand names, no logos, no text in the image.\n` +
    `- Output JSON: {"scene_en": "..."}\n\n` +
    `INPUT (Portuguese):\n` +
    `Tema: ${input.tema ?? "—"}\n` +
    `Capa título: ${input.tituloCapa}\n` +
    `Capa subtítulo: ${input.subtitulo || "—"}`;

  const r = await chat(prompt, TRANSLATOR_SYSTEM);
  if (!r.ok) return { ok: false, error: r.error };
  let parsed: { scene_en?: string };
  try {
    parsed = JSON.parse(r.content);
  } catch {
    return { ok: false, error: "Descrição da cena: JSON inválido." };
  }
  const scene = (parsed.scene_en ?? "").trim();
  if (!scene) return { ok: false, error: "Descrição vazia." };
  return { ok: true, sceneEn: scene };
}
