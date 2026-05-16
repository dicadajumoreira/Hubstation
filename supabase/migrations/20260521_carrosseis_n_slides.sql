-- =============================================================
-- Sindicompany Comunicação — Número de slides do carrossel.
-- Editora escolhe de 1 a 10 slides no form de novo carrossel.
-- Default 6 (média recomendada pelo SKILL.md).
-- =============================================================

alter table public.carrosseis
  add column if not exists n_slides smallint not null default 6
    check (n_slides >= 1 and n_slides <= 10);
