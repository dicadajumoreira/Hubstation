# Skill — sindicompany-carrossel

Gerador de carrosséis 4K para Instagram da Sindicompany (@sindicompanybr).
Saída: PNGs individuais em **3072×3839 (4K vertical 4:5)** + HTML autocontido + legenda Instagram.

## Conteúdo

- `SKILL.md` — especificação completa da skill (regras, fluxo, paleta, tipografia).
- `scripts/helpers.py` — helpers Python pra montar o HTML dos slides com identidade visual.
- `scripts/process_assets.py` — processa logos/patterns brutos pro formato consumido pela skill.
- `scripts/render_4k.py` — renderiza HTML → PNGs 4K via Playwright.
- `assets/fonts/*.woff2` — Epilogue (400, 600, 700, 800, 900) embarcadas como base64.

## Integração com o painel

A área `/sindicompany/carrossel` no painel (Next.js) coleta o briefing da
editora e cria o registro na tabela `carrosseis`. A geração efetiva dos
PNGs acontece via skill rodando manualmente (ou via workflow GitHub Actions
em fase futura).

Fluxo completo planejado:

1. Editora preenche briefing no painel
2. Sistema cria registro `carrosseis` com `status=rascunho` e a foto no Supabase Storage
3. (futuro) Workflow dispara `render_4k.py` com input package serializado
4. PNGs são subidos pro Storage e o registro vira `status=publicada`

Hoje (fase 1), os passos 3 e 4 são manuais.
