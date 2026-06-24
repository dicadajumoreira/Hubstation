-- =============================================================
-- Marcas — paleta (Fase 2: identidade visual data-driven, cores)
-- =============================================================
-- Adiciona marcas.paleta (jsonb) com as cores da marca. O engine
-- (carrossel_generate.py::_palette) faz merge: base chumbada da marca
-- sobreposta pelos valores daqui. Chaves = as MESMAS que o template usa
-- (onix, mint, sand, lavender, purple, white, gray_5).
--
-- Seed = valores IDENTICOS aos chumbados hoje (PALETTE / PALETTE_CONSVICTA)
-- pra garantir ZERO regressao nas 3 marcas atuais. Marca nova define a sua
-- pela tela de cadastro; sem paleta no DB, o engine cai no tema base.

alter table public.marcas add column if not exists paleta jsonb;

-- Sindicompany + By: paleta Brand Hub 2026-05-17 (Navy/Cyan/Beige/...).
update public.marcas set paleta = $j${
  "onix": "#182028",
  "mint": "#88c8d0",
  "sand": "#e0b098",
  "lavender": "#bfc0ff",
  "purple": "#8890d0",
  "white": "#ffffff",
  "gray_5": "#faf7f2"
}$j$::jsonb
where slug in ('sindicompanybr', 'bysindicompany');

-- Consvicta: paleta do brand book (Warm Onix/Tiffany/Ouro/...).
update public.marcas set paleta = $j${
  "onix": "#1a1714",
  "mint": "#81d8d0",
  "sand": "#b08d57",
  "lavender": "#c9a96e",
  "white": "#fdfcf9",
  "gray_5": "#f5f5f2"
}$j$::jsonb
where slug = 'consvictabr';
