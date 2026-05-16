-- =============================================================
-- Sindicompany - Logotipo do condominio (separado do logo do sindico)
-- =============================================================
-- O campo `logo_url` em condominios_meta passa a representar o
-- logotipo do(a) sindico(a) (default usado nas revistas e contracapas).
-- Esta migration adiciona um campo independente pra o logotipo
-- oficial do condominio, usado opcionalmente em outros pontos da
-- comunicacao (nao substitui o do sindico na revista).

alter table public.condominios_meta
  add column if not exists logo_condominio_url text;
