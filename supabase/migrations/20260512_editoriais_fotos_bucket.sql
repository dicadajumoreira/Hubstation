-- =============================================================
-- Sindicompany Comunicação — Bucket pra foto de capa do editorial.
-- Cole no SQL Editor do Supabase e clique RUN.
-- =============================================================
--
-- A foto de capa de cada edição mensal vai aparecer dentro da
-- revista PDF, então o bucket é público (igual condominios-fotos).

insert into storage.buckets (id, name, public)
values ('editoriais-fotos', 'editoriais-fotos', true)
on conflict (id) do nothing;
