-- =============================================================
-- Sindicompany Carrossel - objetivo do carrossel (PASSO 0)
-- =============================================================
-- Define o que o carrossel precisa provocar: comentarios (debate),
-- salvamentos (utilidade), clientes (conversao) ou educar (surpresa).
-- Muda tom, gancho, formato ideal, CTA, construcao dos slides e o
-- criterio de sucesso. Aplicado principalmente ao @sindicompanybr.

alter table public.carrosseis
  add column if not exists objetivo text;
