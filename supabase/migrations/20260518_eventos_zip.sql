-- =============================================================
-- Sindicompany Comunicação — Substitui o link Drive de eventos por
-- upload de ZIP. O ZIP contém subpastas (cada uma vira página
-- exclusiva de evento) com fotos dentro.
-- =============================================================

alter table public.revistas
  add column if not exists eventos_zip_url text;
