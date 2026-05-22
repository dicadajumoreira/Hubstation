-- =============================================================
-- Marcas — temperatura emocional (0-10)
-- =============================================================
-- Dial de intensidade emocional da copy por marca. Escala:
--   0-2 institucional · 3-4 leve · 5-6 emocional · 7-8 provocador ·
--   9-10 extremamente intenso.
-- Entra no prompt de geracao de copy (openai-text) e ajusta hook, CTA,
-- escolha de palavras, ritmo e intensidade. NULL = neutro (sem ajuste;
-- a persona da marca controla).

alter table public.marcas add column if not exists temperatura smallint;

-- Seed das marcas internas (pontos medios das faixas sugeridas).
update public.marcas set temperatura = 7 where slug in ('sindicompanybr', 'bysindicompany');
update public.marcas set temperatura = 4 where slug = 'consvictabr';
