-- =============================================================
-- Sindicompany Comunicação — Logo do condomínio + gestor por revista.
-- Cole no SQL Editor do Supabase e clique RUN.
-- =============================================================
--
-- Mudanças nesta migration:
--
-- 1. logo_url no cadastro do condomínio: cada condomínio passa a
--    ter seu próprio logotipo, que substitui o "Sindicompany" na
--    capa e contracapa da revista daquele condo.
--
-- 2. gestor_foto_url em revistas: o gestor sai do cadastro
--    permanente do condomínio e passa a ser por edição. As
--    colunas tem_gestor / gestor_nome em revistas já existem
--    desde a migration 20260508 — só faltava a foto.

alter table public.condominios_meta
  add column if not exists logo_url text;

alter table public.revistas
  add column if not exists gestor_foto_url text;
