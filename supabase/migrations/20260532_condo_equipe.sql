-- =============================================================
-- Sindicompany - Equipe de Atendimento do condominio + opcao de
-- ocultar contato do sindico (quando tem gestor) — usados na
-- Revista de Boas-Vindas.
-- =============================================================

alter table public.condominios_meta
  -- array de ate 5: [{nome, cargo, foto_path}]
  add column if not exists equipe_atendimento jsonb,
  add column if not exists ocultar_contato_sindico boolean not null default false;
