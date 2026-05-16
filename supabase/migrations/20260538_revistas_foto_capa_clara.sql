-- =============================================================
-- Sindicompany - flag de brilho da foto da capa
-- =============================================================
-- A editora marca se o fundo da foto da capa e claro. Em condominios
-- By Sindicompany, isso determina qual versao do logo "by sindicompany"
-- aparece em destaque na capa: LOGO 1 (fundo escuro / default) ou
-- LOGO 2 (fundo claro).

alter table public.revistas
  add column if not exists foto_capa_clara boolean not null default false;
