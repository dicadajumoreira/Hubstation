-- =============================================================
-- Sindicompany - email e whatsapp do sindico e do gestor
-- =============================================================
-- Campos de contato no cadastro do condominio.

alter table public.condominios_meta
  add column if not exists sindico_email text,
  add column if not exists sindico_whatsapp text,
  add column if not exists gestor_email text,
  add column if not exists gestor_whatsapp text;
