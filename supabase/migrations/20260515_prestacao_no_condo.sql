-- =============================================================
-- Sindicompany Comunicação — Move o arquivo de prestação de contas
-- para condominios_meta (cada condomínio tem o seu, não cada revista).
--
-- Antes da migration: a coluna ficava em `revistas.prestacao_arquivo_url`
-- (criada em 20260514). Mudamos pra condominios_meta porque a editora
-- mantém um único dashboard por condomínio, atualizado mês a mês.
-- =============================================================

alter table public.condominios_meta
  add column if not exists prestacao_arquivo_url text;

-- Mantém a coluna antiga em revistas pra não perder dados de edições
-- já criadas, mas a engine deixa de lê-la. Pode ser removida no futuro.
