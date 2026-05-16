/**
 * Cliente leve da OpenAI Chat Completions API pra geração de copy
 * de carrossel Instagram. Sem dependência externa — fetch direto.
 */

import type { CarrosselCopy, CarrosselSlide } from "./carrosseis";

const OPENAI_API = "https://api.openai.com/v1/chat/completions";

/** Instruções detalhadas por formato de carrossel. Só o bloco do
 *  formato escolhido é injetado no prompt — mantém o prompt enxuto. */
const FORMATO_INSTRUCOES: Record<string, string> = {
  historia_real:
    `FORMATO: HISTÓRIA REAL (o que mais engaja e salva).\n` +
    `- Dê NOME ao personagem (Renata, Lucas, Carlos), nunca "um morador".\n` +
    `- Detalhes concretos: "6 kg", "4 horas", "23%", "Ap. 8B" — tornam crível.\n` +
    `- A história tem virada: setup → conflito → descoberta → resolução.\n` +
    `- Personagens/situações podem ser compostos. NUNCA invente condomínios ou endereços reais.\n` +
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
// Persona por marca. As duas marcas pertencem ao mesmo ecossistema mas tem
// objetivo, publico e linguagem COMPLETAMENTE diferentes:
//   @sindicompanybr -> fala COM o morador comum. Educa, desmistifica.
//   @bysindicompany -> fala COM o sindico profissional / aspirante. Aspiracional,
//                      provocativa, estrategica, empresarial. Vende estrutura,
//                      pertencimento, crescimento, posicionamento, autoridade.
// ---------------------------------------------------------------------------
const SYSTEM_SINDICOMPANYBR =
  "Você é redator do Instagram @sindicompanybr (Sindicompany — síndicos " +
  "profissionais, SP e RJ). VOCÊ FALA COM O MORADOR COMUM do condomínio — " +
  "não com o síndico. Escreve como pessoa inteligente corrigindo um amigo, " +
  "NUNCA como empresa instruindo cliente. Voz: começa dentro da cabeça do " +
  "leitor, frases curtas (um sujeito, um predicado, acabou), tom direto. " +
  "Português brasileiro com TODOS os acentos corretos (você, síndico, " +
  "condomínio, gestão, está, são). " +
  "PROIBIDO: gerúndio (evitando, garantindo, proporcionando), linguagem " +
  "corporativa (soluções integradas, atendimento acolhedor, gestão " +
  "eficiente, excelência), frases de introdução (é importante ressaltar, " +
  "levando em consideração, nesse contexto, vale destacar), CTA comercial " +
  "em corpo de post educativo (Fale com a Sindicompany, Entre em contato), " +
  "travessão (—), aspas curvas (“ ”), emoji decorativo, negrito mecânico. " +
  "Use apenas aspas retas (\"). Sempre termine cada post (legenda) com " +
  "'Por mais lares. 🏡'.";

const SYSTEM_BYSINDICOMPANY =
  "Você é redator do Instagram @bysindicompany — a marca da Sindicompany " +
  "voltada para SÍNDICOS PROFISSIONAIS, pessoas que querem entrar na " +
  "sindicatura e síndicos em crescimento. VOCÊ NÃO FALA COM O MORADOR — " +
  "fala com quem GERE (ou quer gerir) condomínios profissionalmente, e com " +
  "parceiros estratégicos do mercado. Tom: ASPIRACIONAL, PROVOCATIVO, " +
  "ESTRATÉGICO, EMPRESARIAL. Você vende ESTRUTURA, PERTENCIMENTO, " +
  "CRESCIMENTO, POSICIONAMENTO, AUTORIDADE, DESENVOLVIMENTO PROFISSIONAL, " +
  "ESCALA, NETWORKING e SUPORTE. Cada post precisa: atrair síndicos, gerar " +
  "desejo de pertencimento, fortalecer a marca pessoal do síndico, mostrar " +
  "que existe estrutura e suporte por trás, transmitir sensação de rede " +
  "forte e crescimento, elevar o nível da sindicatura profissional. " +
  "Escreve como MENTOR que já chegou onde o leitor quer chegar — não como " +
  "empresa vendendo serviço, não como guru motivacional vazio. Português " +
  "brasileiro com TODOS os acentos corretos. " +
  "PROIBIDO: gerúndio (evitando, garantindo, proporcionando), linguagem " +
  "corporativa vazia (soluções integradas, sinergia, excelência, " +
  "transformação digital), clichê motivacional (o sucesso é uma jornada, " +
  "acredite no seu potencial, saia da zona de conforto, o céu é o limite), " +
  "frases de introdução (é importante ressaltar, vale destacar, nesse " +
  "contexto), travessão (—), aspas curvas (“ ”), emoji decorativo, negrito " +
  "mecânico. Use apenas aspas retas (\"). Sempre termine cada post " +
  "(legenda) com 'By Sindicompany. Sindicatura no próximo nível.'";

const SYSTEM_CONSVICTABR =
  "Você é redator do Instagram @consvictabr (Consvicta — Gestão Condominial " +
  "Boutique, SP & RJ, desde 2019). " +
  "MARCA: Consvicta é uma ADMINISTRADORA BOUTIQUE de condomínios. NÃO é " +
  "plataforma de gestão. É equipe especializada que conhece cada prédio de " +
  "perto. Cada condomínio tem seu próprio jeito de funcionar; cada " +
  "balancete é personalizado; cada plano de contas é customizado. Mais de " +
  "20 anos de experiência no mercado condominial. Tagline oficial: " +
  "'Administração condominial que entrega resultado.' " +
  "PÚBLICO: você fala com SÍNDICOS PROFISSIONAIS, conselheiros consultivos, " +
  "proprietários atentos e tomadores de decisão de prédios de alto padrão " +
  "em SP e RJ. NÃO fala com o morador comum. " +
  "TOM: premium, próximo, técnico mas humano. Confiante sem ser arrogante. " +
  "Pensamento estruturado, frases curtas e diretas, voz própria. Português " +
  "brasileiro com TODOS os acentos corretos. " +
  "VENDE: experiência (20+ anos), atendimento boutique (não plataforma), " +
  "personalização real (balancete e plano de contas sob medida), proximidade, " +
  "decisão informada, prédio tratado como único, gente que conhece o seu " +
  "condomínio pelo nome. " +
  "NÃO VENDE: tecnologia genérica, dashboard padrão, escala, 'transformação " +
  "digital', velocidade barata. " +
  "PROIBIDO: gerúndio decorativo (evitando, garantindo, proporcionando, " +
  "destacando), linguagem corporativa vazia (soluções integradas, sinergia, " +
  "excelência, transformação digital, atendimento acolhedor), clichê " +
  "motivacional (acredite no seu potencial, saia da zona de conforto, o " +
  "céu é o limite), frases de introdução (é importante ressaltar, vale " +
  "destacar, nesse contexto), travessão (—), aspas curvas (“ ”), " +
  "emoji decorativo, negrito mecânico. Use apenas aspas retas (\"). " +
  "Sempre termine cada post (legenda) com 'Consvicta. Administração " +
  "condominial que entrega resultado.'";

function _systemPrompt(brand: string): string {
  if (brand === "bysindicompany") return SYSTEM_BYSINDICOMPANY;
  if (brand === "consvictabr") return SYSTEM_CONSVICTABR;
  return SYSTEM_SINDICOMPANYBR;
}

async function chat(
  prompt: string,
  brand = "sindicompanybr",
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
          { role: "system", content: _systemPrompt(brand) },
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

// PASSO 0 — objetivo do carrossel (@sindicompanybr). Define o que o
// post precisa provocar: muda tom, gancho, formato ideal, CTA, slides
// e criterio de sucesso. Um carrossel = UMA intencao principal.
const OBJETIVO_INSTRUCOES: Record<string, string> = {
  comentarios:
    `OBJETIVO: GERAR COMENTÁRIOS (DEBATE).\n` +
    `- O carrossel PRECISA dividir opiniões com dois lados reconhecíveis. Sucesso = discussão nos comentários, não alcance.\n` +
    `- CTA SEMPRE binário, duas respostas opostas fáceis de comentar: "SIM ou NÃO", "CONCORDO ou DISCORDO", "MORADOR CERTO ou SÍNDICO CERTO", "MULTARIA ou RELEVARIA", "BARULHO NORMAL ou FALTA DE BOM SENSO". NUNCA "o que você acha?", "comenta aqui", "me conta sua opinião" — CTA aberto reduz comentários.\n` +
    `- O tema precisa ter DOIS lados defensáveis. Sem conflito legítimo não há debate.\n` +
    `- Estrutura: gancho forte → crescimento de tensão → situação reconhecível → dois lados claros no final. O ÚLTIMO SLIDE nomeia explicitamente os dois lados — o leitor precisa saber exatamente o que comentar.\n` +
    `- Não cite lei como muleta; o foco é o conflito humano, não a aula jurídica.`,
  salvamentos:
    `OBJETIVO: GERAR SALVAMENTOS (UTILIDADE).\n` +
    `- O post precisa ser tão útil que o leitor queira guardar pra consultar depois. Sensação: "vou precisar disso um dia". Sucesso = salvamentos, compartilhamentos, envio em grupos de condomínio. Comentários NÃO são prioridade.\n` +
    `- Linguagem objetiva, confiável, MENOS emocional — percepção de "referência".\n` +
    `- SEMPRE que possível ancore: lei, artigo, norma, jurisprudência, regra prática, números. Destaque visual pra artigos, números, regras e exceções (use o título do slide pra isso).\n` +
    `- CTA foca em SALVAR: "Salva esse post.", "Guarda isso antes de precisar.", "Manda no grupo do condomínio.", "Você vai precisar disso um dia." NUNCA CTA de debate.\n` +
    `- Estrutura: títulos extremamente claros, leitura rápida, uma ideia por slide, informação escaneável.`,
  clientes:
    `OBJETIVO: ATRAIR NOVOS CLIENTES.\n` +
    `- Síndicos/conselheiros/moradores insatisfeitos precisam perceber que vivem um problema de GESTÃO. Sucesso = DMs, leads, pedidos de orçamento, cliques no link da bio.\n` +
    `- NUNCA venda diretamente. Mostre o caos, a dor, o "antes" e o resultado final. O leitor pensa: "meu condomínio está exatamente assim".\n` +
    `- Problemas que funcionam: inadimplência alta, obras paradas, conflitos internos, falta de transparência, má comunicação, fundo zerado, manutenção negligenciada, assembleia desorganizada, síndico ausente, excesso de reclamações.\n` +
    `- Resultado SEMPRE com números reais: economia, redução de inadimplência, prazo de obra, valorização, organização. Específico converte mais que promessa genérica.\n` +
    `- A marca PODE aparecer mais, o logo pode ter protagonismo, e a tagline "Por mais lares." pode entrar no fechamento.\n` +
    `- CTA leve, nunca anúncio direto: "Seu condomínio está assim?", "A gente resolve.", "Fala com a gente.", "Link na bio.".`,
  educar:
    `OBJETIVO: EDUCAR MORADORES.\n` +
    `- Ensinar algo que o morador não sabe mas deveria saber. Gatilho: SURPRESA + IDENTIFICAÇÃO. A surpresa importa mais que a aula.\n` +
    `- Linguagem MUITO acessível. Sem juridiquês, sem tom professoral. EVITAR "conforme previsto", "nos termos legais", "cumpre esclarecer". PREFERIR "a maioria não sabe, mas...", "isso quase ninguém te explica", "tem condomínio errando isso".\n` +
    `- Estrutura: primeiro mostra o problema que o morador já conhece; depois explica o que ele não sabia. Uma ideia por slide, progressão lógica, conclusão clara antes do CTA.\n` +
    `- CTA depende do tema: muito útil → "Salva esse post"; divide opiniões → CTA binário de debate.\n` +
    `- Sucesso: "não sabia disso", "meu condomínio faz errado", compartilhamentos, salvamentos, marcações de vizinhos.`,
};

// PASSO 0 — objetivo do carrossel (@consvictabr). Consvicta e marca
// boutique de gestao condominial (SP & RJ, desde 2019). Publico:
// sindico profissional / conselho / proprietario de prediol alto
// padrao. Tom: premium, proximo, tecnico-mas-humano. Vende experiencia
// boutique e personalizacao real. NUNCA mencionar Sindicompany ou By
// Sindicompany — sao marcas distintas e concorrentes do ponto de
// vista do conteudo.
const OBJETIVO_INSTRUCOES_CONSVICTA: Record<string, string> = {
  comentarios:
    `OBJETIVO: GERAR COMENTÁRIOS (DEBATE QUALIFICADO).\n` +
    `- Provoca síndicos profissionais, conselheiros e proprietários atentos a comentar com opinião. Sucesso = debate qualificado, não alcance.\n` +
    `- CTA binário com lados defensáveis: "PERSONALIZADO ou PADRÃO", "BOUTIQUE ou PLATAFORMA", "TÉCNICO ou COMERCIAL", "TRANSPARÊNCIA ou EFICIÊNCIA", "COBRARIA ou RELEVARIA".\n` +
    `- Temas: gestão padronizada × atendimento sob medida, balancete genérico × personalizado, plataforma × pessoa, custo barato × valor entregue, decisão rápida × decisão informada.\n` +
    `- NUNCA polêmica vazia ou ataque pessoal. Debate é sobre PRÁTICA de mercado.`,
  salvamentos:
    `OBJETIVO: GERAR SALVAMENTOS (REFERÊNCIA TÉCNICA).\n` +
    `- O post precisa ser tão útil que vire material de consulta. Sensação: "vou usar isso na próxima assembleia/decisão". Sucesso = salvamentos, envios em grupo, citação em reunião de conselho.\n` +
    `- Linguagem técnica mas humana — sem juridiquês decorativo. Ancore: lei, artigo, número, jurisprudência, prática de mercado.\n` +
    `- Temas: balancete vs prestação de contas, prestação personalizada × padrão, plano de contas customizado, fundo de reserva, leitura de DRE de condomínio, indicadores de gestão, sinais de gestão amadora.\n` +
    `- CTA "Salva esse post.", "Leva pra próxima reunião do conselho.", "Manda pro síndico que cuida do seu prédio.".`,
  clientes:
    `OBJETIVO: ATRAIR NOVOS CONDOMÍNIOS (PREMIUM).\n` +
    `- Quem decide trocar a administração precisa perceber que vive um problema BOUTIQUE: prédio único tratado como mais um, balancete padrão sem leitura, conselho sem interlocução técnica, decisões pelo formulário em vez de pela conversa.\n` +
    `- Mostre o caos típico: balancete que ninguém entende, gestor que troca a cada 6 meses, prestação atrasada, conselho atropelado, plano de contas que não casa com o prédio. Resultado SEMPRE com número real: prazo, economia, redução de inadimplência, retomada de obras.\n` +
    `- NUNCA prometa transformação digital, dashboard, tecnologia mágica. Venda: equipe especializada, atendimento próximo, balancete sob medida, plano de contas customizado, 20+ anos de mercado, gente que conhece o prédio pelo nome.\n` +
    `- CTA elegante e seletivo: "O seu prédio merece uma administração que conhece ele pelo nome.", "Marca uma conversa.", "Talvez sua administração esteja te tratando como mais um.".`,
  autoridade:
    `OBJETIVO: POSICIONAR AUTORIDADE BOUTIQUE NO MERCADO.\n` +
    `- Eleva a Consvicta como REFERÊNCIA em gestão condominial boutique de SP & RJ. Não é vender agora — é fazer o mercado pensar "essa administradora opera num outro nível". Sucesso = compartilhamentos qualificados, citação em mesa de conselho, percepção de elite.\n` +
    `- Linguagem sofisticada, técnica, MENOS emocional. Visão de mercado, profissionalização do setor, futuro da administração condominial, gestão por dados, transparência, proximidade.\n` +
    `- Temas: futuro da administração condominial, o erro de tratar prédio como template, por que balancete personalizado importa, o que diferencia gestão boutique de plataforma, sinais de uma administradora de elite, leitura crítica de prestação de contas.\n` +
    `- CTA institucional: "A administração condominial mudou.", "Há gestão para gente, e gestão para template.", "Por uma administração que olha no olho.".`,
};

// PASSO 0 — objetivo do carrossel (@bysindicompany). Mesma ideia do
// @sindicompanybr, mas o publico e o sindico PROFISSIONAL — muda
// linguagem, dor, gatilhos, formatos, CTA e percepcao de valor. O
// conteudo nao pode parecer perfil de condominio: parece mercado,
// posicionamento, bastidor da sindicatura, crescimento, autoridade.
const OBJETIVO_INSTRUCOES_BY: Record<string, string> = {
  comentarios:
    `OBJETIVO: GERAR COMENTÁRIOS (DEBATE ENTRE SÍNDICOS).\n` +
    `- Provoca identificação e divisão entre síndicos profissionais. Sucesso = síndicos debatendo, marcando outros síndicos, comentários longos, identificação profissional.\n` +
    `- O síndico precisa sentir vontade de defender sua visão de gestão. Linguagem mais madura, mais direta, mais "mercado" — sensação de "finalmente alguém falou isso".\n` +
    `- CTA binário ou altamente posicionável: "SÍNDICO OPERACIONAL ou SÍNDICO ESTRATÉGICO", "COBRARIA ou RELEVARIA", "DEMITIRIA ou TREINARIA", "WHATSAPP AJUDA ou ATRAPALHA", "GESTÃO FIRME ou GESTÃO LEVE". Nunca CTA genérico.\n` +
    `- Temas que funcionam: síndico que faz tudo sozinho, excesso de WhatsApp, condômino invasivo, conselho tóxico, síndico que não delega, guerra de ego entre síndicos, concorrência desleal, preço baixo no mercado, síndrome do síndico 24h, romantização da sobrecarga. NUNCA tema de "dica de condomínio" pro morador.`,
  salvamentos:
    `OBJETIVO: GERAR SALVAMENTOS (CRESCIMENTO PROFISSIONAL).\n` +
    `- O post precisa AJUDAR O SÍNDICO A CRESCER PROFISSIONALMENTE. Sensação: "isso melhora minha gestão". Parece ferramenta, framework, referência, aprendizado aplicável, visão estratégica. Sucesso = salvamentos, compartilhamentos entre síndicos, reposts, encaminhamento em grupos de gestão.\n` +
    `- Útil pra: operação, posicionamento, liderança, comunicação, vendas, gestão, organização, expansão. Muito escaneável, muito prático — o síndico aplica, adapta, salva pra rever.\n` +
    `- Temas: como cobrar sem perder autoridade, como conduzir assembleias difíceis, erros que fazem síndicos perder condomínios, como parar de apagar incêndio, como construir marca pessoal, como precificar sindicatura, sinais de gestão desorganizada, como criar processos, como lidar com conselho hostil, o que síndicos de alto nível fazem diferente.\n` +
    `- CTA: "Salva isso.", "Todo síndico precisa guardar esse post.", "Você vai usar isso em alguma assembleia.", "Manda pra outro síndico." Nunca CTA de debate.`,
  clientes:
    `OBJETIVO: ATRAIR SÍNDICOS PARA O BY SINDICOMPANY.\n` +
    `- O síndico precisa pensar "eu não quero crescer sozinho". Atrai quem quer escala, estrutura, marca, backoffice, crescer no mercado, parar de só sobreviver. Sucesso = DMs, inscrições, leads qualificados, pedidos de reunião.\n` +
    `- NUNCA vender como franquia. NUNCA parecer recrutamento comum. O By precisa parecer ELITE DE MERCADO, estrutura profissional, crescimento, posicionamento, fortalecimento de marca pessoal.\n` +
    `- Mostrar: bastidores reais, estrutura, equipe, suporte, marketing, engenharia, jurídico, processos, networking, crescimento profissional, fortalecimento do nome do síndico. Contraste síndico-sozinho × síndico-com-estrutura.\n` +
    `- Dor: síndico cansado de fazer tudo sozinho, operar sem equipe, ser refém do WhatsApp, não conseguir crescer, perder tempo operacional, não construir autoridade.\n` +
    `- Linguagem aspiracional, estratégica, mercado premium — "é esse nível que eu quero atingir".\n` +
    `- CTA seletivo, nunca anúncio: "Talvez o próximo passo da sua sindicatura seja esse.", "Nem todo síndico está pronto para crescer assim.", "Se você quer crescer de verdade, fala com a gente.", "O mercado mudou. E alguns síndicos cresceram junto."`,
  autoridade:
    `OBJETIVO: POSICIONAR AUTORIDADE NO MERCADO.\n` +
    `- Eleva a percepção do By Sindicompany como REFERÊNCIA em sindicatura profissional. Não é vender agora — é fazer o síndico pensar "eles estão alguns passos à frente do mercado". Sucesso = compartilhamentos entre síndicos, percepção de autoridade, convites, networking, fortalecimento da marca.\n` +
    `- Linguagem sofisticada, estratégica, MENOS emocional, MENOS humor — visão de mercado, liderança, experiência, movimento de transformação da sindicatura.\n` +
    `- Temas: futuro da sindicatura, profissionalização do mercado, erros estruturais do setor, gestão orientada por dados, construção de marca, crescimento sustentável, síndico como empresário, liderança, posicionamento, mercado premium, comportamento do novo morador.\n` +
    `- CTA institucional e elegante: "O mercado mudou.", "A sindicatura está evoluindo.", "Os síndicos que entenderem isso primeiro sairão na frente.", "Por mais síndicos preparados."\n` +
    `- Formatos fortes aqui: Manifesto, tendência de mercado, dado que choca, visão estratégica, carta aberta, reflexão profissional.`,
};

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
  const brand =
    input.brand === "bysindicompany"
      ? "bysindicompany"
      : input.brand === "consvictabr"
        ? "consvictabr"
        : "sindicompanybr";
  const isBy = brand === "bysindicompany";
  const isConsvicta = brand === "consvictabr";
  const objMap = isConsvicta
    ? OBJETIVO_INSTRUCOES_CONSVICTA
    : isBy
      ? OBJETIVO_INSTRUCOES_BY
      : OBJETIVO_INSTRUCOES;
  const objetivoBloco =
    input.objetivo && objMap[input.objetivo]
      ? `\n${objMap[input.objetivo]}\n`
      : "";
  const formato_label = input.formato.replaceAll("_", " ");
  const instrucoesFormato =
    FORMATO_INSTRUCOES[input.formato] ??
    `FORMATO: ${formato_label} (estrutura livre, mantendo a voz e os 7 passos).`;

  const assinatura = isConsvicta
    ? "Consvicta. Administração condominial que entrega resultado."
    : isBy
      ? "By Sindicompany. Sindicatura no próximo nível."
      : "Por mais lares. 🏡";

  const handle = isConsvicta
    ? "@consvictabr"
    : isBy
      ? "@bysindicompany"
      : "@sindicompanybr";

  const blocoEstrategia = isConsvicta
    ? `ESTRATÉGIA @consvictabr:\n` +
      `- PÚBLICO: síndico profissional, conselho consultivo, proprietário atento, tomador de decisão de prédio premium em SP & RJ. NUNCA o morador comum.\n` +
      `- OBJETIVO DA MARCA: posicionar a Consvicta como administradora BOUTIQUE — equipe especializada que conhece cada prédio de perto. NÃO é plataforma de gestão.\n` +
      `- TOM: premium, próximo, técnico mas humano. Confiante sem ser arrogante. Frases curtas e diretas. Sem cliché motivacional, sem corporativo vazio.\n` +
      `- VENDE: experiência (20+ anos), atendimento boutique, balancete personalizado, plano de contas customizado, proximidade, decisão informada, prédio tratado como único.\n` +
      `- NÃO VENDE: dashboard, plataforma, transformação digital, escala, tecnologia genérica.\n`
    : isBy
      ? `ESTRATÉGIA @bysindicompany:\n` +
        `- PÚBLICO: síndico profissional / aspirante / em crescimento / parceiro estratégico. NUNCA o morador.\n` +
        `- OBJETIVO DA MARCA: atrair síndicos, gerar pertencimento, fortalecer a marca pessoal do síndico, mostrar estrutura/suporte, elevar o nível da sindicatura.\n` +
        `- TOM: aspiracional, provocativo, estratégico, empresarial. Mentor que já chegou. NUNCA guru motivacional vazio.\n`
      : `ESTRATÉGIA @sindicompanybr:\n` +
        `- PÚBLICO: o MORADOR comum do condomínio. NUNCA o síndico.\n` +
        `- OBJETIVO: educar, desmistificar, virar referência que se salva e se compartilha.\n` +
        `- TOM: pessoa inteligente corrigindo um amigo. Direto, sem rodeio.\n`;

  const blocoContexto = isConsvicta
    ? `- Contexto: gestão condominial BOUTIQUE — administradora que conhece o prédio pelo nome. Quando falar de condomínio, é pelo ângulo de DECISÃO, GOVERNANÇA, PRESTAÇÃO DE CONTAS, RELAÇÃO conselho × administradora. Pelo menos UM slide menciona "condomínio", "administração condominial" ou "gestão" literal.\n`
    : isBy
      ? `- Contexto: bastidores e realidade da SINDICATURA PROFISSIONAL — gestão, liderança, mercado, carreira, estrutura. Quando falar de condomínio, é pelo ângulo de quem GERE, não de quem mora. Pelo menos UM slide menciona "síndico"/"sindicatura"/"gestão" literal.\n`
      : `- Contexto condominial sempre: assembleia, taxa, síndico, morador, área comum, regulamento, convivência, fachada, manutenção. Pelo menos UM slide menciona "condomínio" ou "condominial" literal.\n`;

  const angulos = isConsvicta
    ? [
        "Recorte: o erro de tratar prédio como template (gestão padronizada × boutique).",
        "Recorte: governança e transparência (balancete personalizado, plano de contas sob medida, leitura crítica de prestação de contas).",
        "Recorte: experiência e proximidade (20+ anos, equipe que conhece o condomínio pelo nome, decisão informada do conselho).",
      ]
    : isBy
      ? [
          "Recorte: dor / solidão / desafio do síndico (o que ninguém fala).",
          "Recorte: crescimento / posicionamento / autoridade (como subir de nível).",
          "Recorte: rede / estrutura / pertencimento (não estar sozinho, ter suporte).",
        ]
      : [
          "Recorte: morador comum (apartamento, garagem, elevador, convivência doméstica).",
          "Recorte: governança/financeiro (assembleia, taxa, prestação de contas, fundo de reserva).",
          "Recorte: o que o morador espera do síndico/gestão.",
        ];

  const listaNegraExtra = isBy
    ? ", o sucesso é uma jornada, acredite no seu potencial, saia da zona de conforto, mindset vencedor"
    : isConsvicta
      ? ", transformação digital, soluções integradas, atendimento acolhedor, escala, plataforma de gestão"
      : "";

  const antiLeak = isConsvicta
    ? `- PROIBIDO mencionar "Sindicompany", "By Sindicompany", "@sindicompanybr", "@bysindicompany" ou qualquer outra administradora/marca além da Consvicta. Concorrentes NUNCA aparecem nos slides nem na legenda.\n` +
      `- PROIBIDO usar a tagline "Por mais lares" — essa NÃO é a tagline da Consvicta. A tagline correta é "Administração condominial que entrega resultado." e só aparece na legenda.\n`
    : "";

  const buildPrompt = (angulo: string): string =>
    `Crie UMA versão de copy pra um carrossel do ${handle}.\n\n` +
    `${blocoEstrategia}` +
    objetivoBloco +
    `\nBRIEFING:\n` +
    `- Título interno: ${input.titulo}\n` +
    `- Tema: ${input.tema}\n` +
    `- Formato: ${formato_label}\n` +
    `- Quantidade de slides: ${input.n_slides}\n` +
    (input.briefing ? `- Contexto extra: ${input.briefing}\n` : "") +
    `- ${angulo}\n` +
    `\n${instrucoesFormato}\n\n` +
    (objetivoBloco
      ? `IMPORTANTE: o OBJETIVO acima é a intenção PRINCIPAL — quando objetivo e formato divergirem, o objetivo manda (CTA, tom, estrutura).\n\n`
      : "") +
    `VOZ: CENA concreta (começa no meio) → SUPOSIÇÃO do leitor (termina com "né?"/"certo?") → CONTRADIÇÃO em ≤3 palavras → EXPLICAÇÃO uma ideia por frase → FECHAMENTO paradoxal/quotável → CTA. A ASSINATURA "${assinatura}" aparece SÓ na legenda, nunca nos slides. Use a estrutura de slides do FORMATO.\n\n` +
    `REGRAS:\n` +
    `- Capa: o tema "${input.tema}" aparece literal ou em paráfrase clara. Capa inteira (titulo + body) tem no máximo 20 palavras.\n` +
    `- Cada slide interno: tipo + título (3-7 palavras) + body (1-3 frases curtas, máx 35 palavras). Seja conciso — não encha linguiça.\n` +
    `- Em posts educativos (mito, dado, tutorial, lista jurídica): pelo menos UMA âncora — artigo (ex: "Código Civil, art. 1.336"), decisão judicial (ex: "STJ, REsp 1.699.022/SP, 2019") OU dado com fonte nomeada e datada.\n` +
    blocoContexto +
    antiLeak +
    `- LEGENDA Instagram: 4-8 linhas, hook na primeira, termina OBRIGATORIAMENTE com "${assinatura}" e EXATAMENTE 3 hashtags na linha seguinte${isConsvicta ? ' (use #consvicta + 2 hashtags do tema — JAMAIS #sindicompany ou #bysindicompany)' : ""}.\n` +
    `- Acentos corretos em TODA palavra (você, síndico, condomínio, gestão). NUNCA: gerúndio, travessão (—), aspas curvas, emoji decorativo no slide, frases de introdução ("é importante ressaltar").\n` +
    `- LISTA NEGRA: papel fundamental, momento crucial, cenário em constante evolução, destacando a importância, o futuro é promissor, juntos somos mais fortes, destaca-se, vibrante, no coração de, em meio a, reflete a, simboliza a, evidencia a, desafios e oportunidades, rica diversidade, não apenas X mas também Y, mergulhando em, celebrando a, fomentando o, estudos mostram, especialistas afirmam${listaNegraExtra}.\n\n` +
    `Devolva JSON estrito (sem markdown):\n` +
    `{ "slides": [{"tipo":"capa","titulo":"...","body":"..."}, ... total ${input.n_slides} slides], "legenda":"..." }`;

  // 3 chamadas em PARALELO, uma por angulo — cada uma e pequena (~6 slides
  // + legenda), entao termina rapido e cabe folgado no cap de 26s do
  // Netlify. Antes era uma chamada unica gerando as 3 versoes, que
  // estourava o tempo limite com o prompt grande.
  let results: ({ ok: true; content: string } | { ok: false; error: string })[];
  try {
    results = await Promise.all(angulos.map((a) => chat(buildPrompt(a), brand)));
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

  const r = await chat(prompt);
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

  const r = await chat(prompt);
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
