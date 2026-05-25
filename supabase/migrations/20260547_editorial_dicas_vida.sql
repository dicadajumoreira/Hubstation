-- =============================================================
-- Editorial mensal — temas de Dicas Práticas e Vida Condominial
-- =============================================================
-- Acrescenta os campos de tema que faltavam pra organizar o editorial
-- na sequência da revista:
--   - dicas_praticas_temas: temas das Dicas Práticas (S05). Texto livre
--     (um tema por linha); a IA usa como guia ao gerar as dicas.
--   - vida_condominial_tema: tema da matéria de Vida Condominial (S12B).

alter table public.editoriais_mensais
  add column if not exists dicas_praticas_temas text,
  add column if not exists vida_condominial_tema text;
