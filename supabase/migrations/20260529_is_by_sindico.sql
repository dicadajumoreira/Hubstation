-- =============================================================
-- Sindicompany - sindico By Sindicompany
-- =============================================================
-- Quando o sindico de um condominio faz parte do By Sindicompany,
-- a revista usa o logotipo do By (bucket __by-logos) no lugar do
-- logo Sindicompany: fundo branco -> LOGO 2, fundo escuro -> LOGO 1.

alter table public.condominios_meta
  add column if not exists is_by_sindico boolean not null default false;

-- Flag copiada pra a revista no momento de criar a edicao, pra o
-- engine saber qual logo usar.
alter table public.revistas
  add column if not exists is_by_sindico boolean not null default false;
