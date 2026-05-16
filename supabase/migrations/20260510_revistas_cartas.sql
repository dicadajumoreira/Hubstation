-- =============================================================
-- Sindicompany Comunicação — Cartas do síndico e do gestor.
-- Cole no SQL Editor do Supabase e clique RUN.
-- =============================================================
--
-- Campos pra editar (ou aceitar a sugestão automática) o tema e
-- o conteúdo das duas cartas. A carta do gestor só sai impressa
-- na revista se o condomínio tiver gestor cadastrado.

alter table public.revistas
  add column if not exists carta_sindico_tema text,
  add column if not exists carta_sindico_texto text,
  add column if not exists carta_gestor_tema text,
  add column if not exists carta_gestor_texto text;
