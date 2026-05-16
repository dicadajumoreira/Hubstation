-- =============================================================
-- Sindicompany Comunicação — Carrosséis Instagram (@sindicompanybr)
--
-- Geração de carrosséis 4K (3072x3839, 4:5) baseada na skill
-- 'sindicompany-carrossel'. Cada carrossel é um post composto por
-- N slides PNG + uma legenda Instagram, todos gerados a partir de
-- briefing + foto da capa fornecidos pela editora.
-- =============================================================

create table if not exists public.carrosseis (
  id uuid default gen_random_uuid() primary key,
  titulo text not null,
  tema text,
  formato text,
  briefing text,
  foto_capa_url text,
  status text not null default 'rascunho'
    check (status in ('rascunho', 'em_producao', 'publicada', 'erro')),
  png_paths text[] default '{}',
  legenda text,
  erro_mensagem text,
  gerado_em timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.carrosseis disable row level security;

create index if not exists idx_carrosseis_created_at
  on public.carrosseis (created_at desc);
