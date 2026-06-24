-- =============================================================
-- Sindicompany Carrossel - arquetipo de capa (Brand Hub 2026-05-17)
-- =============================================================
-- Permite a editora escolher por carrossel qual arquetipo do Brand
-- Hub novo usar na capa (Cover 01 Editorial Question, Cover 02 Dark
-- Premium, etc.). Valores aceitos sincronizados com
-- COVER_ARCHETYPES_SC do revista-engine/api/carrossel_generate.py.
--
-- Default null = usa o fallback da env var SINDICOMPANY_COVER_ARCHETYPE
-- (legado) ou a capa classica se a env var nao estiver setada. Permite
-- migracao sem big-bang.

alter table public.carrosseis
  add column if not exists cover_archetype text;
