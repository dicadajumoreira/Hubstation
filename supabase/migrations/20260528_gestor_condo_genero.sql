-- =============================================================
-- Sindicompany - Gestor de Atendimento por condominio (genero)
-- =============================================================
-- O gestor agora e cadastrado na tela de Condominios (nao mais por
-- edicao na revista). Pode ser homem ('Gestor de Atendimento') ou
-- mulher ('Gestora de Atendimento') — o titulo sai do genero.

alter table public.condominios_meta
  add column if not exists gestor_genero text;

-- gestor_titulo na revista: texto pronto ('Gestor de Atendimento' ou
-- 'Gestora de Atendimento') copiado do cadastro do condo no momento
-- de criar a edicao. O engine usa pra renderizar a carta/contracapa.
alter table public.revistas
  add column if not exists gestor_titulo text;
