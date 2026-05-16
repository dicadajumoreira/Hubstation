-- =============================================================
-- Sindicompany - Equipe de Atendimento global
-- =============================================================
-- Equipe compartilhada que atende TODOS os condominios (em vez de uma
-- equipe por condo). Usada no Expediente e na nova pagina S14C
-- "Equipe de Atendimento" da revista mensal (renderizada depois do
-- convite da comunidade, quando o condo tem comunidade cadastrada).

create table if not exists public.equipe_atendimento_global (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  cargo text not null,
  foto_path text,
  ordem int not null default 100,
  created_at timestamptz not null default now()
);

create index if not exists equipe_atendimento_global_ordem_idx
  on public.equipe_atendimento_global (ordem, created_at);
