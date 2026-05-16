-- =============================================================
-- Sindicompany Carrossel - URL do ZIP com todos os PNGs
-- =============================================================
-- Engine empacota todos os slides (slide-1.png .. slide-N.png) num
-- arquivo zip pra a editora baixar de uma vez. URL publica do
-- arquivo no Storage fica nesta coluna.

alter table public.carrosseis
  add column if not exists zip_url text;
