-- =============================================================
-- Sindicompany Comunicação — Tabelas para o backoffice editorial.
-- Cole isso no SQL Editor do Supabase e clique em RUN.
--
-- Acesso é único-via-senha (env var SINDICOMPANY_PASSWORD), então as
-- linhas NÃO ficam atadas a auth.users — RLS desativada e o acesso é
-- mediado pela camada Next.js + service_role.
-- =============================================================

create extension if not exists "uuid-ossp";

create table if not exists public.revistas (
  id uuid primary key default uuid_generate_v4(),
  condominio text not null,
  mes int not null check (mes between 1 and 12),
  ano int not null check (ano between 2024 and 2030),
  status text not null default 'em_producao'
    check (status in ('em_producao', 'publicada', 'erro')),
  pdf_storage_path text,
  paginas int,
  gerado_em timestamptz,
  erro_mensagem text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (condominio, mes, ano)
);

create index if not exists idx_revistas_condominio on public.revistas(condominio);
create index if not exists idx_revistas_status on public.revistas(status);
create index if not exists idx_revistas_data on public.revistas(ano desc, mes desc);

-- Trigger para updated_at (reusa função de schema.sql, ou cria local)
create or replace function public.touch_revistas_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_revistas_touch on public.revistas;
create trigger trg_revistas_touch before update on public.revistas
  for each row execute function public.touch_revistas_updated_at();

-- =============================================================
-- Storage bucket para PDFs gerados.
-- Via Supabase Studio → Storage:
--   - bucket name: revistas-pdfs
--   - public: false (URLs assinadas)
-- (não é possível criar buckets via SQL — fazer manualmente)
-- =============================================================

-- Sem RLS: backoffice usa service_role e gerencia acesso na camada Next.js
alter table public.revistas disable row level security;
