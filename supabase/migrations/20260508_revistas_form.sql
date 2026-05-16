-- =============================================================
-- Sindicompany Comunicação — Campos do form de Nova Edição.
-- Cole no SQL Editor do Supabase e clique RUN.
-- =============================================================

alter table public.revistas
  add column if not exists sindico_nome text,
  add column if not exists sindico_genero text check (sindico_genero in ('masculino', 'feminino')),
  add column if not exists tem_gestor boolean not null default false,
  add column if not exists gestor_nome text,
  add column if not exists drive_manutencao_url text,
  add column if not exists drive_prestacao_url text,
  add column if not exists tem_advertencias boolean not null default false,
  add column if not exists multas_advertencias_obs text,
  add column if not exists tem_eventos boolean not null default false,
  add column if not exists drive_eventos_url text,
  add column if not exists materia_capa_titulo text,
  add column if not exists materia_capa_subtitulo text,
  add column if not exists foto_capa_url text,
  add column if not exists receita_sugerida text,
  add column if not exists receita_titulo text,
  add column if not exists notas_editor text;
