-- =============================================================
-- Sindicompany Carrossel - URLs de foto por slide
-- =============================================================
-- Permite a editora subir uma foto especifica pra cada slide
-- (alem da foto IA da capa). Array indexado por posicao do slide
-- 0-based. Posicoes vazias usam o fundo padrao do tema/pattern.

alter table public.carrosseis
  add column if not exists slide_fotos text[];
