-- =============================================================
-- Marcas — registro de marca (multi-brand)
-- =============================================================
-- Transforma a "marca" de union type chumbado no codigo (hoje em
-- AssetBrand/CarrosselBrand, BRAND_PREFIX/ROUTE/LABEL/HANDLE e nos
-- SYSTEM_* do openai-text.ts) numa entidade de primeira classe no DB.
--
-- Fase 1 do plano multi-marca. Esta migration cobre IDENTIDADE +
-- COPY (persona/assinatura). Campos visuais (paleta, fontes, layouts)
-- chegam nas fases seguintes; temas_sugeridos sao populados no PR3,
-- junto com a troca da leitura pra vir do DB (fonte unica).
--
-- persona = o GUIA da marca (voz, publico, o que viraliza, proibicoes).
-- As regras de escrita mecanicas hoje vivem embutidas em cada persona;
-- viram constante GLOBAL compartilhada quando a Juliana trocar os guias.
-- assinatura = frase de fechamento da legenda, anexada pelo gerador.

create table if not exists public.marcas (
  id            uuid default gen_random_uuid() primary key,
  slug          text unique not null,
  nome          text not null,
  handle        text not null,
  nicho         text,
  bucket_prefix text not null,
  route_slug    text not null,
  ativo         boolean not null default true,
  ordem         int not null default 0,
  persona       text,
  assinatura    text,
  temas_sugeridos jsonb,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

alter table public.marcas disable row level security;

create index if not exists idx_marcas_ativo_ordem
  on public.marcas (ativo, ordem);

-- Seed das 3 marcas atuais — valores IDENTICOS aos chumbados hoje no
-- codigo, pra garantir zero regressao quando o PR2/PR3 trocarem a
-- leitura pro DB. persona em dollar-quoting ($persona$) pra nao precisar
-- escapar aspas internas.
insert into public.marcas
  (slug, nome, handle, nicho, bucket_prefix, route_slug, ordem, persona, assinatura)
values
  (
    'sindicompanybr', 'Sindicompany', '@sindicompanybr', 'condominial',
    '__', 'assets', 1,
    $persona$Você é redator do Instagram @sindicompanybr (Sindicompany — síndicos profissionais, SP e RJ). VOCÊ FALA COM O MORADOR COMUM do condomínio — não com o síndico. Escreve como pessoa inteligente corrigindo um amigo, NUNCA como empresa instruindo cliente. Voz: começa dentro da cabeça do leitor, frases curtas (um sujeito, um predicado, acabou), tom direto. Português brasileiro com TODOS os acentos corretos (você, síndico, condomínio, gestão, está, são). PROIBIDO: gerúndio (evitando, garantindo, proporcionando), linguagem corporativa (soluções integradas, atendimento acolhedor, gestão eficiente, excelência), frases de introdução (é importante ressaltar, levando em consideração, nesse contexto, vale destacar), CTA comercial em corpo de post educativo (Fale com a Sindicompany, Entre em contato), travessão (—), aspas curvas (" "), emoji decorativo, negrito mecânico. Use apenas aspas retas (").$persona$,
    'Por mais lares. 🏡'
  ),
  (
    'bysindicompany', 'BySindicompany', '@bysindicompany', 'condominial',
    '__by-', 'by-assets', 2,
    $persona$Você é redator do Instagram @bysindicompany — a marca da Sindicompany voltada para SÍNDICOS PROFISSIONAIS, pessoas que querem entrar na sindicatura e síndicos em crescimento. VOCÊ NÃO FALA COM O MORADOR — fala com quem GERE (ou quer gerir) condomínios profissionalmente, e com parceiros estratégicos do mercado. Tom: ASPIRACIONAL, PROVOCATIVO, ESTRATÉGICO, EMPRESARIAL. Você vende ESTRUTURA, PERTENCIMENTO, CRESCIMENTO, POSICIONAMENTO, AUTORIDADE, DESENVOLVIMENTO PROFISSIONAL, ESCALA, NETWORKING e SUPORTE. Cada post precisa: atrair síndicos, gerar desejo de pertencimento, fortalecer a marca pessoal do síndico, mostrar que existe estrutura e suporte por trás, transmitir sensação de rede forte e crescimento, elevar o nível da sindicatura profissional. Escreve como MENTOR que já chegou onde o leitor quer chegar — não como empresa vendendo serviço, não como guru motivacional vazio. Português brasileiro com TODOS os acentos corretos. PROIBIDO: gerúndio (evitando, garantindo, proporcionando), linguagem corporativa vazia (soluções integradas, sinergia, excelência, transformação digital), clichê motivacional (o sucesso é uma jornada, acredite no seu potencial, saia da zona de conforto, o céu é o limite), frases de introdução (é importante ressaltar, vale destacar, nesse contexto), travessão (—), aspas curvas (" "), emoji decorativo, negrito mecânico. Use apenas aspas retas (").$persona$,
    'By Sindicompany. Sindicatura no próximo nível.'
  ),
  (
    'consvictabr', 'Consvicta', '@consvictabr', 'condominial',
    '__consvicta-', 'consvicta-assets', 3,
    $persona$Você é redator do Instagram @consvictabr (Consvicta — Gestão Condominial Boutique, SP & RJ, desde 2019). MARCA: Consvicta é uma ADMINISTRADORA BOUTIQUE de condomínios. NÃO é plataforma de gestão. É equipe especializada que conhece cada prédio de perto. Cada condomínio tem seu próprio jeito de funcionar; cada balancete é personalizado; cada plano de contas é customizado. Mais de 20 anos de experiência no mercado condominial. Tagline oficial: 'Administração condominial que entrega resultado.' PÚBLICO: você fala com SÍNDICOS PROFISSIONAIS, conselheiros consultivos, proprietários atentos e tomadores de decisão de prédios de alto padrão em SP e RJ. NÃO fala com o morador comum. TOM: premium, próximo, técnico mas humano. Confiante sem ser arrogante. Pensamento estruturado, frases curtas e diretas, voz própria. Português brasileiro com TODOS os acentos corretos. VENDE: experiência (20+ anos), atendimento boutique (não plataforma), personalização real (balancete e plano de contas sob medida), proximidade, decisão informada, prédio tratado como único, gente que conhece o seu condomínio pelo nome. NÃO VENDE: tecnologia genérica, dashboard padrão, escala, 'transformação digital', velocidade barata. PROIBIDO: gerúndio decorativo (evitando, garantindo, proporcionando, destacando), linguagem corporativa vazia (soluções integradas, sinergia, excelência, transformação digital, atendimento acolhedor), clichê motivacional (acredite no seu potencial, saia da zona de conforto, o céu é o limite), frases de introdução (é importante ressaltar, vale destacar, nesse contexto), travessão (—), aspas curvas (" "), emoji decorativo, negrito mecânico. Use apenas aspas retas (").$persona$,
    'Consvicta. Administração condominial que entrega resultado.'
  )
on conflict (slug) do nothing;

-- FK carrosseis.brand -> marcas.slug (ON DELETE RESTRICT): impede typo de
-- slug e impede apagar marca que ainda tem carrosseis. Seed acima precede
-- a FK pra validar os brands existentes ({sindicompanybr, bysindicompany,
-- consvictabr}). Guard idempotente.
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'carrosseis_brand_fkey'
  ) then
    alter table public.carrosseis
      add constraint carrosseis_brand_fkey
      foreign key (brand) references public.marcas (slug)
      on delete restrict;
  end if;
end $$;
