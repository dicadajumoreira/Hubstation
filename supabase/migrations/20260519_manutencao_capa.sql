-- =============================================================
-- Sindicompany Comunicação — Foto de capa do caderno 'Nosso Condomínio'
-- (S08) escolhida manualmente pela editora. Antes era auto-selecionada
-- do ZIP de manutenção pela engine. Agora a editora pode subir uma
-- foto específica pra capa via novo input no form.
-- =============================================================

alter table public.revistas
  add column if not exists manutencao_capa_url text;
