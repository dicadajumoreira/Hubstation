-- =============================================================
-- Sindicompany Comunicação — Editorial mensal compartilhado.
-- Cole no SQL Editor do Supabase e clique RUN.
-- =============================================================
--
-- O editorial é decidido UMA VEZ por mês e vale pra todas as
-- revistas daquele mês (matéria de capa, foto, receita, temas
-- sugeridos das cartas). A parte específica de cada condomínio
-- continua na tabela `revistas`.

create table if not exists public.editoriais_mensais (
  mes smallint not null check (mes between 1 and 12),
  ano smallint not null check (ano between 2025 and 2030),
  materia_capa_titulo text,
  materia_capa_subtitulo text,
  foto_capa_url text,
  receita_titulo text,
  receita_descricao text,
  carta_sindico_tema text,
  carta_gestor_tema text,
  notas_editor_geral text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (mes, ano)
);

create or replace function public.touch_editoriais_mensais_updated_at()
returns trigger as $$
begin
  new.updated_at := now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_editoriais_mensais_updated_at on public.editoriais_mensais;
create trigger trg_editoriais_mensais_updated_at
  before update on public.editoriais_mensais
  for each row execute function public.touch_editoriais_mensais_updated_at();
