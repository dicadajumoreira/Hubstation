-- =============================================================
-- Sindicompany - Comunicados (avisos aos moradores)
-- =============================================================
-- Comunicados sao gerados em 2 formatos (A4 e Celular). O texto pode
-- ser digitado pela editora OU gerado por IA a partir de um briefing.
-- A ilustracao do canto superior direito e enviada por comunicado;
-- o logo do condominio e o logo By Sindicompany vem do cadastro/assets.

create table if not exists public.comunicados (
  id uuid primary key default gen_random_uuid(),
  condominio text not null,
  titulo text not null,
  subtitulo text,
  briefing text,
  corpo text not null default '',
  ilustracao_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists comunicados_created_at_idx on public.comunicados (created_at desc);
