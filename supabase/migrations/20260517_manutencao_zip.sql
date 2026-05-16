-- =============================================================
-- Sindicompany Comunicação — Substitui o link Drive de manutenção
-- por upload de ZIP. O ZIP contém subpastas (cada uma vira card de
-- manutenção) com fotos dentro.
--
-- A coluna drive_manutencao_url fica preservada como legado mas o
-- sistema deixa de usá-la — preferência sempre pelo ZIP.
-- =============================================================

alter table public.revistas
  add column if not exists manutencao_zip_url text;
