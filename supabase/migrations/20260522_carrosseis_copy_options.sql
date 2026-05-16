-- =============================================================
-- Sindicompany Comunicação — Wizard de carrossel em 3 etapas:
-- 1. Briefing (titulo, tema, formato, n_slides)
-- 2. Editora escolhe entre 3 opções de copy geradas pela IA
-- 3. Foto da capa (upload ou IA com base na copy escolhida)
-- =============================================================

alter table public.carrosseis
  add column if not exists copy_options jsonb,
  add column if not exists copy_selected smallint
    check (copy_selected is null or (copy_selected >= 0 and copy_selected <= 9));
