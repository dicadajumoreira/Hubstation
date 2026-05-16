-- =============================================================
-- Sindicompany - Dupla de sindicos e dupla de gestores
-- =============================================================
-- Permite cadastrar UM SEGUNDO sindico(a) e UM SEGUNDO gestor(a) por
-- condominio. Quando presentes, a revista (boas-vindas e mensal) usa
-- voz plural e concordancia gramatical apropriada.

alter table public.condominios_meta
  add column if not exists sindico2_nome text,
  add column if not exists sindico2_genero text,
  add column if not exists sindico2_foto_path text,
  add column if not exists sindico2_email text,
  add column if not exists sindico2_whatsapp text,
  add column if not exists gestor2_nome text,
  add column if not exists gestor2_genero text,
  add column if not exists gestor2_foto_path text,
  add column if not exists gestor2_email text,
  add column if not exists gestor2_whatsapp text;

alter table public.condominios_meta
  drop constraint if exists condominios_meta_sindico2_genero_check;
alter table public.condominios_meta
  add constraint condominios_meta_sindico2_genero_check
  check (sindico2_genero is null or sindico2_genero in ('masculino', 'feminino', 'empresa'));

alter table public.condominios_meta
  drop constraint if exists condominios_meta_gestor2_genero_check;
alter table public.condominios_meta
  add constraint condominios_meta_gestor2_genero_check
  check (gestor2_genero is null or gestor2_genero in ('masculino', 'feminino'));
