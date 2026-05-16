-- =============================================================
-- Sindicompany Comunicação — Campo de upload do dashboard de prestação
-- de contas (imagem ou PDF). Substitui o uso de link do Drive em
-- "Nossos Números" pra extração de KPIs via Vision/OCR.
-- =============================================================

alter table public.revistas
  add column if not exists prestacao_arquivo_url text;
