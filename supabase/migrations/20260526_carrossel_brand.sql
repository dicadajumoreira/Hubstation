-- =============================================================
-- Sindicompany Carrossel - dimensao de marca (brand)
-- =============================================================
-- Permite criar carrosseis pra mais de um Instagram: @sindicompanybr
-- (default) e @bysindicompany. O engine usa o brand pra escolher
-- handle, logo e buckets de assets (__by-patterns/, __by-icons/, etc).

alter table public.carrosseis
  add column if not exists brand text not null default 'sindicompanybr';
