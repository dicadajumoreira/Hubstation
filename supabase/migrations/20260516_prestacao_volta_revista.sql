-- =============================================================
-- Sindicompany Comunicação — Volta o arquivo de prestação de contas
-- pra `revistas` (cada edição tem o seu — muda mês a mês).
--
-- A coluna em condominios_meta (criada em 20260515) é descartada.
-- Se você já tinha subido valores lá, eles serão perdidos — mas não
-- há perda real porque o pipeline de geração de revista nunca chegou
-- a usar esse caminho em produção.
--
-- A coluna em revistas.prestacao_arquivo_url já existe (migration
-- 20260514), basta voltar a usá-la.
-- =============================================================

alter table public.condominios_meta
  drop column if exists prestacao_arquivo_url;
