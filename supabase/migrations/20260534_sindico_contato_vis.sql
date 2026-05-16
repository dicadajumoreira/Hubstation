-- =============================================================
-- Sindicompany - visibilidade do contato do sindico na revista
-- =============================================================
-- Substitui o flag unico 'ocultar_contato_sindico' por dois flags
-- granulares: a editora escolhe se aparece o WhatsApp e/ou o e-mail
-- do(a) sindico(a) na Revista de Boas-Vindas. Default: ambos visiveis.

alter table public.condominios_meta
  add column if not exists mostrar_whatsapp_sindico boolean not null default true,
  add column if not exists mostrar_email_sindico boolean not null default true;
