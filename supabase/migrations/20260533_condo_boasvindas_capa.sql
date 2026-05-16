-- =============================================================
-- Sindicompany - foto de capa da Revista de Boas-Vindas (por condo)
-- =============================================================

alter table public.condominios_meta
  add column if not exists boasvindas_capa_path text;
