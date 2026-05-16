-- =============================================================
-- Sindicompany - link da comunidade + QR code no cadastro do condo
-- =============================================================

alter table public.condominios_meta
  add column if not exists comunidade_url text,
  add column if not exists comunidade_qrcode_path text;
