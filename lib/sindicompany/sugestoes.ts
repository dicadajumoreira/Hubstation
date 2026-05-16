/**
 * Sugestões editoriais por mês.
 *
 * Quando o(a) editor(a) abre "Nova edição", a engine sugere uma matéria
 * de capa e uma receita baseadas no mês. São apenas sugestões — pode
 * sobrescrever na hora.
 *
 * Mantenha as matérias temáticas e leves. Aproveitar datas marcantes
 * (Páscoa, junho, outubro rosa, dezembro) sem ficar engessado.
 */

export interface SugestaoMaterial {
  titulo: string;
  subtitulo: string;
}

export interface SugestaoReceita {
  titulo: string;
  descricao: string;
}

export interface SugestaoCarta {
  tema: string;
  resumo: string;
}

const MATERIA_POR_MES: Record<number, SugestaoMaterial> = {
  1: {
    titulo: "Começo de ano: o condomínio também recomeça",
    subtitulo: "O que vale revisar em janeiro: orçamento, regimento e a convivência depois das férias.",
  },
  2: {
    titulo: "Verão sob controle: água, energia e ar-condicionado",
    subtitulo: "Como passar fevereiro com a conta no azul e a casa fresca.",
  },
  3: {
    titulo: "Outono chegando: revisar estrutura antes da chuva",
    subtitulo: "Calhas, telhados, fachadas — o que ainda dá tempo de checar.",
  },
  4: {
    titulo: "O condomínio que ama pets vive melhor",
    subtitulo: "Convivência, regulação e bons exemplos para áreas comuns.",
  },
  5: {
    titulo: "Outono no prédio: aconchego e contas em ordem",
    subtitulo: "Calefação, água quente e como o condomínio economiza junto.",
  },
  6: {
    titulo: "Festa junina no salão: como fazer dar certo",
    subtitulo: "Organização, segurança e boa vizinhança numa noite só.",
  },
  7: {
    titulo: "Inverno: isolamento térmico e o silêncio do prédio",
    subtitulo: "Pequenos ajustes que mudam o conforto e a conta de luz.",
  },
  8: {
    titulo: "Saúde mental e convivência condominial",
    subtitulo: "O que a vizinhança pode (e não pode) fazer por quem mora ao lado.",
  },
  9: {
    titulo: "Primavera, jardins e áreas comuns que florescem",
    subtitulo: "Paisagismo, manutenção e o impacto visual do prédio.",
  },
  10: {
    titulo: "Outubro Rosa: cuidar da saúde começa em casa",
    subtitulo: "Iniciativas simples que o condomínio pode apoiar.",
  },
  11: {
    titulo: "Novembro Azul + reta final do ano",
    subtitulo: "Saúde do homem e o que ainda dá pra fechar antes de dezembro.",
  },
  12: {
    titulo: "Festas de fim de ano sem dor de cabeça",
    subtitulo: "Segurança, fogos, pets e a regra de ouro: combinar antes.",
  },
};

const RECEITA_POR_MES: Record<number, SugestaoReceita> = {
  1: { titulo: "Salada tropical de manga e camarão",   descricao: "Refrescante para o calor de janeiro." },
  2: { titulo: "Bowl de açaí com granola caseira",      descricao: "Energia gelada para o verão." },
  3: { titulo: "Bolo de fubá cremoso",                   descricao: "Conforto de início de outono." },
  4: { titulo: "Colomba pascal recheada",                descricao: "Sobra de páscoa virou ouro." },
  5: { titulo: "Sopa de abóbora com gengibre",           descricao: "Cremosa e leve para esquentar a noite." },
  6: { titulo: "Quentão de inverno",                     descricao: "Festa junina dentro de casa." },
  7: { titulo: "Caldo verde tradicional",                descricao: "Couve, batata e linguiça — clássico." },
  8: { titulo: "Strogonoff de frango cremoso",           descricao: "Família reunida no domingo." },
  9: { titulo: "Bolo de cenoura com cobertura",          descricao: "A primavera no café da tarde." },
  10: { titulo: "Brigadeiro rosa no copinho",            descricao: "Outubro Rosa que cabe na bandeja." },
  11: { titulo: "Risoto de cogumelos com parmesão",      descricao: "Sofisticado e fácil." },
  12: { titulo: "Panettone caseiro de chocolate",        descricao: "O cheiro de Natal pelo apartamento." },
};

/**
 * Tema sugerido pra carta do(a) síndico(a) — fala de gestão,
 * convivência e visão pro mês.
 */
const CARTA_SINDICO_POR_MES: Record<number, SugestaoCarta> = {
  1: { tema: "Um novo ciclo começa", resumo: "Boas-vindas pro ano novo, prioridades de gestão e o que esperar dos próximos meses." },
  2: { tema: "Verão e convivência", resumo: "Pequenas regras que tornam o convívio mais leve nas férias e no calor." },
  3: { tema: "Volta à rotina, foco no condomínio", resumo: "Com escolas voltando, é hora de revisar segurança, áreas comuns e prazos." },
  4: { tema: "Comunidade que cuida", resumo: "Páscoa como mote pra falar de gentileza, vizinhança e ações coletivas." },
  5: { tema: "Outono: revisões e prevenção", resumo: "O que a gestão está olhando antes do frio chegar de vez." },
  6: { tema: "Tradição e união", resumo: "Festa junina, calor humano em meio ao frio, e por que celebrar junto importa." },
  7: { tema: "Meio do ano: balanço de gestão", resumo: "O que foi feito até agora e o que vem pelo segundo semestre." },
  8: { tema: "Saúde mental no condomínio", resumo: "Como pequenas atitudes coletivas reduzem estresse e ruído na convivência." },
  9: { tema: "Primavera no prédio", resumo: "Renovação visual, paisagismo e ações de embelezamento." },
  10: { tema: "Outubro Rosa", resumo: "Como o condomínio apoia a campanha e a saúde da comunidade feminina." },
  11: { tema: "Novembro Azul + reta final", resumo: "Saúde do homem e prioridades pro fechamento do ano." },
  12: { tema: "Encerrando o ano com gratidão", resumo: "Balanço, agradecimentos e o que esperar pro próximo ciclo." },
};

/**
 * Tema sugerido pra carta do gestor — operacional, próximo do dia a dia
 * dos moradores, complementa a carta do síndico.
 */
const CARTA_GESTOR_POR_MES: Record<number, SugestaoCarta> = {
  1: { tema: "Atendimento renovado", resumo: "Como falar com o gestor, novos canais e horários de atendimento no ano novo." },
  2: { tema: "Manutenções de verão", resumo: "O que está em andamento e como reportar problemas com calor e chuvas." },
  3: { tema: "Preparando o prédio pro outono", resumo: "Cronograma de manutenções preventivas, calhas e telhados." },
  4: { tema: "Recados rápidos da gestão", resumo: "Pets, áreas comuns e regras que evitam atrito no dia a dia." },
  5: { tema: "Energia, água e a conta no fim do mês", resumo: "Pequenas ações coletivas que afetam o boleto." },
  6: { tema: "Salão de festas: como reservar", resumo: "Procedimentos, taxas e dicas pra evitar dor de cabeça." },
  7: { tema: "Inverno: aquecedores, infiltração e ruído", resumo: "Cuidados práticos pra essa época do ano." },
  8: { tema: "Vizinhança que se ajuda", resumo: "Canais de denúncia, mediação de conflitos e protocolo de zeladoria." },
  9: { tema: "Áreas comuns no foco", resumo: "Reformas pequenas, jardim, piscina e brinquedoteca: cronograma." },
  10: { tema: "Saúde e prevenção no condomínio", resumo: "Iniciativas que a gestão está apoiando e como participar." },
  11: { tema: "Reta final: agendamentos pra dezembro", resumo: "Reservas de salão, mudanças e prazos de fim de ano." },
  12: { tema: "Festas, segurança e mudanças", resumo: "Procedimentos especiais pro mês mais movimentado do ano." },
};

export function sugerirMateria(mes: number): SugestaoMaterial | null {
  return MATERIA_POR_MES[mes] ?? null;
}

export function sugerirReceita(mes: number): SugestaoReceita | null {
  return RECEITA_POR_MES[mes] ?? null;
}

export function sugerirCartaSindico(mes: number): SugestaoCarta | null {
  return CARTA_SINDICO_POR_MES[mes] ?? null;
}

export function sugerirCartaGestor(mes: number): SugestaoCarta | null {
  return CARTA_GESTOR_POR_MES[mes] ?? null;
}
