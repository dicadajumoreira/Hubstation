-- =============================================================
-- Sindicompany Comunicação — Metadados do condomínio.
-- Guarda síndico/gestor (nome + gênero + foto) por condomínio,
-- pra que a engine reaproveite em todas as edições da revista.
--
-- Cole no SQL Editor do Supabase e clique RUN.
-- =============================================================

create table if not exists public.condominios_meta (
  nome text primary key,
  sindico_nome text,
  sindico_genero text check (sindico_genero in ('masculino', 'feminino')),
  sindico_foto_path text,
  tem_gestor boolean not null default false,
  gestor_nome text,
  gestor_foto_path text,
  updated_at timestamptz not null default now()
);

-- Bucket público pras fotos dos síndicos/gestores.
-- Público porque vão aparecer dentro da revista em PDF, então
-- ler via URL direta simplifica. (Ninguém vai listar o bucket.)
insert into storage.buckets (id, name, public)
values ('condominios-fotos', 'condominios-fotos', true)
on conflict (id) do nothing;

-- Trigger pra manter updated_at sempre fresco.
create or replace function public.touch_condominios_meta_updated_at()
returns trigger as $$
begin
  new.updated_at := now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_condominios_meta_updated_at on public.condominios_meta;
create trigger trg_condominios_meta_updated_at
  before update on public.condominios_meta
  for each row execute function public.touch_condominios_meta_updated_at();
