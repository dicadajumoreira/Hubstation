/**
 * Hierarquia oficial de Assets do Sindicompany.info.
 *
 * Organizada em 4 PILARES (conforme handoff do Brand Hub):
 *   1. Brand Assets       — institucional/fixo da marca
 *   2. Social Media       — capas, carrosseis, CTAs, elementos
 *   3. Visual Library     — patterns, fotografia, backgrounds, icones
 *   4. AI Ready Assets    — prompts, composicoes, regras, templates
 *
 * Estrutura por marca: cada uma das 3 marcas (Sindicompany,
 * BySindicompany, Consvicta) tem sua propria copia completa desta arvore.
 *
 * Levels:
 *   1. Brand    (definido no path da rota: /assets, /by-assets, /consvicta-assets)
 *   2. Pillar   (Brand Assets, Social Media, ...)
 *   3. Category (Logotipos, Capas, Patterns, Prompts Visuais, ...)
 *   4. Leaf     (asset slot — onde upload acontece)
 *
 * Cada leaf gera um bucket prefix no Supabase Storage no formato:
 *   __{brand-prefix}{pillar}-{category}-{leaf}
 *
 * Onde brand-prefix = "" (Sindicompany), "by-" (By), "consvicta-".
 */

import type { MarcaSlug } from "@/lib/sindicompany/marcas-db";

// Slug da marca. A lista valida (e os metadados: prefixo, rota, nome,
// handle) vive na tabela `marcas` (marcas-db.ts). Use getMarca(slug).
export type AssetBrand = MarcaSlug;

export interface AssetNode {
  slug: string;
  label: string;
  description?: string;
  children?: AssetNode[];
  /** Se setado, este leaf reusa um bucket legacy (ex: "logos", "patterns")
   *  em vez de derivar do path. Mantem assets ja uploadados acessiveis. */
  legacyBucket?: string;
  /** Quantidade default de slots vazios pra mostrar no AssetSlotGrid
   *  quando ainda nao ha upload. Sem isso, usa 20 (legado). Capas usam
   *  6 porque raramente precisam de muitas variacoes; o botao "+ Novo
   *  slot" continua estendendo dinamicamente quando precisar. */
  slotsDefault?: number;
}

function leaf(
  slug: string,
  label: string,
  opts: { legacyBucket?: string; slotsDefault?: number; description?: string } = {},
): AssetNode {
  return { slug, label, ...opts };
}

export const ASSET_HIERARCHY: AssetNode[] = [
  // ───────────────────────────────────────────────────────────────────
  // 1. Brand Assets
  // ───────────────────────────────────────────────────────────────────
  {
    slug: "brand-assets",
    label: "Brand Assets",
    description: "Institucional e fixo da marca — logos, paleta, tipografia, guidelines",
    children: [
      {
        slug: "logos",
        label: "Logotipos",
        children: [
          // Principal reusa "logos" — mantem uploads ja feitos
          leaf("master", "Master / Principal", { legacyBucket: "logos" }),
          leaf("horizontal-mono", "Horizontal monocromático"),
          leaf("horizontal-duo", "Horizontal duo (combinações cromáticas)"),
          leaf("vertical", "Vertical lockup"),
          leaf("simbolo-mono", "Símbolo mono"),
          leaf("simbolo-duo", "Símbolo duo"),
          leaf("simbolo-foto", "Símbolo com foto"),
          leaf("sobre-fotografia", "Logo sobre fotografia"),
          leaf("containers-badges", "Containers & Badges"),
          leaf("escalas-pequenas", "Escalas pequenas (favicon 16→128px)"),
          leaf("area-protecao", "Área de proteção"),
        ],
      },
      {
        slug: "palette",
        label: "Paleta",
        children: [
          leaf("cores-principais", "6 Cores principais"),
          leaf("neutros", "Neutros (Paper, Line, Muted)"),
          leaf("pares-aprovados", "Pares aprovados"),
          leaf("gradientes", "Gradientes (Aurora, Sunset, Deep Sea, Sand)"),
        ],
      },
      {
        slug: "type",
        label: "Tipografia",
        children: [
          leaf("provicali", "Provicali (wordmark)"),
          leaf("epilogue", "Epilogue (display + body)"),
          leaf("jetbrains-mono", "JetBrains Mono (specs/captions)"),
          leaf("escala", "Escala tipográfica"),
        ],
      },
      {
        slug: "guidelines",
        label: "Guidelines",
        children: [
          leaf("dos", "DOs (3 regras)"),
          leaf("donts", "DON'Ts (6 erros)"),
          leaf("tom-de-voz", "Tom de voz (6 atributos)"),
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────
  // 2. Social Media
  // ───────────────────────────────────────────────────────────────────
  {
    slug: "social-media",
    label: "Social Media",
    description: "Capas, carrosséis, CTAs e elementos gráficos para feed",
    children: [
      {
        slug: "capas",
        label: "Capas (17 arquétipos)",
        description:
          "17 capas selecionadas do Brand Hub. 7 sem foto + 10 com foto. " +
          "Cada leaf começa com 6 slots; estende via “+ Novo slot”.",
        children: [
          // SEM foto (7) — alinhado com CARROSSEL_COVER_ARCHETYPES
          leaf("numbered-guide", "Numbered guide", { slotsDefault: 6, description: "Split número Navy / headline" }),
          leaf("manifesto", "Manifesto", { slotsDefault: 6, description: "Italic gigante sobre fundo Cyan" }),
          leaf("pattern-explosion", "Pattern explosion", { slotsDefault: 6, description: "Pattern topo + card Paper na base" }),
          leaf("sticky-note", "Sticky note", { slotsDefault: 6, description: "Card Beige tipo post-it rotacionado" }),
          leaf("brackets", "Brackets", { slotsDefault: 6, description: "Colchetes Beige gigantes envolvendo headline" }),
          leaf("type-tower", "Type tower", { slotsDefault: 6, description: "Palavras empilhadas em tamanhos crescentes" }),
          leaf("corner-tape", "Corner tape", { slotsDefault: 6, description: "Fitas Cyan diagonais nos 4 cantos + headline centralizada" }),
          // COM foto (10) — consomem a foto da etapa 3 do /carrossel/novo
          leaf("dark-premium", "Dark Premium", { slotsDefault: 6, description: "Foto full + gradient Navy" }),
          leaf("magazine-cover", "Magazine cover", { slotsDefault: 6, description: "Masthead + foto + faixa Paper" }),
          leaf("split-portrait", "Split portrait", { slotsDefault: 6, description: "Foto 45% esquerda + texto 55% Paper" }),
          leaf("hero-portrait", "Hero portrait", { slotsDefault: 6, description: "Foto full + tag mono + box Beige" }),
          leaf("photo-circle", "Foto circular", { slotsDefault: 6, description: "Círculo grande centralizado + texto abaixo" }),
          leaf("photo-banner", "Photo banner", { slotsDefault: 6, description: "Foto top 60% + Paper bottom com headline" }),
          leaf("photo-blur", "Photo blur", { slotsDefault: 6, description: "Foto desfocada como background + headline crisp" }),
          leaf("cinema", "Cinema", { slotsDefault: 6, description: "Foto em faixa cinemascope central" }),
          leaf("polaroid", "Polaroid", { slotsDefault: 6, description: "Foto em moldura polaroid rotacionada com sombra" }),
          leaf("portrait-frame", "Portrait frame", { slotsDefault: 6, description: "Foto em quadro Beige com inner border Navy" }),
        ],
      },
      {
        slug: "carrosseis",
        label: "Carrosséis (7 formatos)",
        description:
          "Biblioteca de referência dos 7 formatos. Cada slug bate 1:1 " +
          "com carrosseis.formato. Preview lê png_paths[0] do último " +
          "carrossel gerado com aquele formato. A geração acontece em " +
          "/sindicompany/carrossel/novo — aqui é só catálogo.",
        children: [
          leaf("historia_real", "História real", { description: "Hook tenso → personagem → erro → virada → resultado com número → CTA SIM/NAO" }),
          leaf("lista", "Lista", { description: "Capa promessa → 1 item por slide (menos óbvio → mais surpreendente) → CTA debate" }),
          leaf("mito_verdade", "Mito vs. Verdade", { description: "Capa pergunta → pares Mito↔Verdade (max 3) com lei/artigo → CTA debate" }),
          leaf("antes_depois", "Antes / Depois", { description: "Dado do depois → antes reconhecível → problema raiz → o que mudou → CTA binário" }),
          leaf("dado_choca", "Dado que choca", { description: "Só o número Black 900 → significado → quem está dentro → contraponto → CTA SIM/NAO" }),
          leaf("tutorial", "Tutorial rápido", { description: "Problema em pergunta → barreira → passos numerados com verbo → modelo copiável → CTA salvar" }),
          leaf("opiniao", "Opinião forte", { description: "Afirmação MAX 6 palavras → motivo → arg1 → contra-arg + resposta → arg2 → CTA CONCORDO/DISCORDO" }),
        ],
      },
      {
        slug: "ctas",
        label: "CTAs (6 templates)",
        description:
          "6 templates de chamada pra ação que fecham o carrossel. Cada " +
          "slug bate 1:1 com carrosseis.cta_template (a ser criada). " +
          "Quando preenchido, sobrescreve o CTA default embedado no flow.",
        children: [
          leaf("comente", "Comente", { description: "Pergunta binária que obriga posicionamento (SIM/NAO, CONCORDO/DISCORDO)" }),
          leaf("compartilhe", "Compartilhe", { description: "Convida a marcar alguém ou enviar pra grupo do condomínio" }),
          leaf("salve", "Salve", { description: "Convida a guardar pra consulta futura (checklist, dado, tutorial)" }),
          leaf("segue", "Segue", { description: "Convida a seguir o perfil pra mais conteúdo do tema" }),
          leaf("whatsapp", "WhatsApp", { description: "Convida a iniciar conversa direta — converte em atendimento" }),
          leaf("link", "Link", { description: "Convida a acessar link da bio — oferta ancorada (PDF, formulário)" }),
        ],
      },
      {
        slug: "elementos",
        label: "Elementos gráficos",
        children: [
          leaf("setas", "Setas (3 estilos)"),
          leaf("tags-labels", "Tags & labels"),
          leaf("boxes", "Boxes (quote/stat/tip)"),
          leaf("molduras", "Molduras casa-shape"),
          leaf("glow-blur", "Glow & blur"),
          leaf("linhas-decorativas", "Linhas decorativas"),
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────
  // 3. Visual Library
  // ───────────────────────────────────────────────────────────────────
  {
    slug: "visual-library",
    label: "Visual Library",
    description: "Patterns, fotografia, backgrounds e ícones",
    children: [
      {
        slug: "patterns",
        label: "Patterns",
        children: [
          // Cantos reusa "patterns" (bucket legado dos uploads atuais)
          leaf("cantos", "Cantos", { legacyBucket: "patterns" }),
          leaf("decorativos", "Decorativos"),
          leaf("criativos", "Criativos (bordas laterais)"),
          leaf("fundos-hero", "Fundos hero compositions"),
          leaf("fundos-tile", "Fundos seamless tile"),
        ],
      },
      {
        slug: "fotografia",
        label: "Fotografia",
        children: [
          leaf("studio-cyan", "Linha Studio Cyan (retratos)"),
          leaf("banco-institucional", "Banco institucional"),
          leaf("tratamentos", "Tratamentos de cor"),
          leaf("dos-donts", "DOs & DON'Ts"),
          leaf("foto-marca", "Aplicação Foto + Marca (50/50)"),
        ],
      },
      {
        slug: "backgrounds",
        label: "Backgrounds (80 = 4 formatos × 20 receitas)",
        children: [
          leaf("1080x1080", "1080 × 1080 (Feed quadrado)"),
          leaf("1080x1350", "1080 × 1350 (Feed 4:5)"),
          leaf("1080x1920", "1080 × 1920 (Story/Reels)"),
          leaf("1080x720", "1080 × 720 (Horizontal)"),
        ],
      },
      {
        slug: "icons",
        label: "Ícones (56 em 7 categorias)",
        children: [
          // Condomínio reusa "icons" (86 ícones Consvicta + atuais Sindicompany)
          leaf("condominio", "Condomínio", { legacyBucket: "icons" }),
          leaf("financeiro", "Financeiro"),
          leaf("juridico", "Jurídico"),
          leaf("engenharia", "Engenharia"),
          leaf("comunicacao", "Comunicação"),
          leaf("manutencao", "Manutenção"),
          leaf("ia", "IA"),
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────
  // 4. AI Ready Assets
  // ───────────────────────────────────────────────────────────────────
  {
    slug: "ai-ready",
    label: "AI Ready Assets",
    description: "Prompts, composições, regras e templates para geração via IA",
    children: [
      {
        slug: "prompts-visuais",
        label: "Prompts Visuais (5 estilos)",
        children: [
          leaf("editorial", "Estilo editorial"),
          leaf("ultra-realista", "Estilo ultra-realista"),
          leaf("instagram", "Estilo Instagram"),
          leaf("pixar-3d", "Estilo Pixar / 3D"),
          leaf("corporativo", "Estilo corporativo"),
        ],
      },
      {
        slug: "composicoes",
        label: "Composições (6 cenários)",
        children: [
          leaf("mulher-executiva", "Mulher executiva"),
          leaf("assembleia", "Assembleia"),
          leaf("area-comum", "Área comum"),
          leaf("sindico-trabalho", "Síndico no trabalho"),
          leaf("prestacao-contas", "Prestação de contas"),
          leaf("conflito", "Conflito condominial"),
        ],
      },
      {
        slug: "regras-visuais",
        label: "Regras Visuais",
        children: [
          leaf("safe-area-instagram", "Safe areas Instagram"),
          leaf("estetica-marca", "Estética da marca"),
          leaf("iluminacao", "Iluminação"),
          leaf("tipografia-imagem", "Tipografia em imagem"),
        ],
      },
      {
        slug: "templates",
        label: "Templates (12 estruturas)",
        children: [
          // Instagram
          leaf("instagram-carrossel", "Instagram · Carrossel"),
          leaf("instagram-reels-cover", "Instagram · Reels cover"),
          leaf("instagram-story", "Instagram · Story"),
          leaf("instagram-feed-unico", "Instagram · Feed único"),
          // Comercial
          leaf("comercial-propostas", "Comercial · Propostas"),
          leaf("comercial-pdfs", "Comercial · PDFs"),
          leaf("comercial-apresentacoes", "Comercial · Apresentações"),
          leaf("comercial-relatorios", "Comercial · Relatórios"),
          // Eventos
          leaf("eventos-convites", "Eventos · Convites"),
          leaf("eventos-credenciais", "Eventos · Credenciais"),
          leaf("eventos-backdrop", "Eventos · Backdrop"),
          leaf("eventos-certificados", "Eventos · Certificados"),
        ],
      },
    ],
  },
];

// ─────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────
// Metadados de marca (prefixo de bucket, rota, nome, handle) NAO vivem
// mais aqui — leia da tabela `marcas` via getMarca(slug) (marcas-db.ts).

export function findNode(path: string[]): AssetNode | null {
  if (path.length === 0) return null;
  let level: AssetNode[] = ASSET_HIERARCHY;
  let found: AssetNode | null = null;
  for (const slug of path) {
    const next = level.find((n) => n.slug === slug);
    if (!next) return null;
    found = next;
    level = next.children ?? [];
  }
  return found;
}

export function bucketForLeaf(
  bucketPrefix: string,
  pathSegments: string[],
  leafNode: AssetNode,
): string {
  const prefix = bucketPrefix;
  if (leafNode.legacyBucket) {
    return `${prefix}${leafNode.legacyBucket}`;
  }
  const slug = pathSegments.join("-");
  return `${prefix}${slug}`;
}

export function basenameForLeaf(leafNode: AssetNode): string {
  if (leafNode.legacyBucket === "patterns") return "pattern";
  if (leafNode.legacyBucket === "icons") return "icon";
  if (leafNode.legacyBucket === "icon-carrossel") return "icon";
  if (leafNode.legacyBucket === "logos") return "logo";
  return leafNode.slug;
}

export function* iterLeaves(
  nodes: AssetNode[] = ASSET_HIERARCHY,
  prefix: string[] = [],
): Generator<{ path: string[]; node: AssetNode }> {
  for (const node of nodes) {
    const current = [...prefix, node.slug];
    if (!node.children || node.children.length === 0) {
      yield { path: current, node };
    } else {
      yield* iterLeaves(node.children, current);
    }
  }
}
