-- =============================================================
-- Sindicompany - permite 'empresa' como tipo de sindicatura
-- =============================================================
-- Antes o sindico_genero so aceitava 'masculino' | 'feminino'. Agora
-- a sindicatura pode ser feita por uma administradora/empresa: nesse
-- caso a revista se dirige aos moradores como uma equipe (1a pessoa
-- do plural). Relaxa o CHECK em condominios_meta e em revistas.

alter table public.condominios_meta
  drop constraint if exists condominios_meta_sindico_genero_check;
alter table public.condominios_meta
  add constraint condominios_meta_sindico_genero_check
  check (sindico_genero in ('masculino', 'feminino', 'empresa'));

alter table public.revistas
  drop constraint if exists revistas_sindico_genero_check;
alter table public.revistas
  add constraint revistas_sindico_genero_check
  check (sindico_genero in ('masculino', 'feminino', 'empresa'));
