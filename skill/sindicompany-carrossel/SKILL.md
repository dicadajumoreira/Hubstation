---
name: sindicompany-carrossel
description: "Gerador de carrosséis 4K para Instagram da Sindicompany (@sindicompanybr). Use SEMPRE que pedirem carrossel, carousel, slides, post para Instagram, conteúdo viral, engajamento de moradores, post sindicompany, gerar conteúdo condomínio, ideia de post, ou qualquer variação. MANDATORY TRIGGERS: carrossel, carousel, slides Instagram, post sindicompany, conteúdo Instagram, gerar post, criar carrossel, conteúdo viral condomínio, engajamento moradores, história real condomínio."
---

# Carrosséis Sindicompany v2

Gerador editorial de carrosséis para o Instagram da **Sindicompany** (@sindicompanybr).
Saída final: PNGs individuais em 3072×3839 (4K vertical 4:5) + HTML autocontido + legenda Instagram.

**Não pergunte sobre marca, cores ou fontes — tudo está definido abaixo.**

## REGRAS INEGOCIÁVEIS

> 🔴 **SLIDE 1:** sempre com foto real (pessoa, cotidiano, ambiente). O texto ocupa apenas a metade de baixo do slide, com overlay gradient escuro. A foto fica livre na metade de cima. Sem exceção.

> 🔴 **SELO DE CASINHA NA CAPA:** a CAPA DEVE conter uma das casinhas `Logotipo_Sindicompany__Icon_1.png` a `Icon_6.png` no canto inferior direito, em opacidade FULL (sem transparência), como selo visual de marca sobrepondo a foto. Use a função `cover_icon_stamp(all_icons, variant=...)` do helpers.py. Default é `variant='mint'` (Icon_2). A capa é o ÚNICO slide que recebe esse selo full opacity.

> 🔴 **ICON DE FUNDO:** todo slide do carrossel (EXCETO a capa) DEVE conter no fundo um dos arquivos `Logotipo_Sindicompany__Icon_1.png` a `Icon_6.png`, aplicado como imagem de fundo sutil atrás do conteúdo. Use a função `background_icon(all_icons, slide_index, light_bg=...)` do helpers.py, que cicla automaticamente entre os icons compatíveis pelo índice do slide. A capa NUNCA recebe icon de fundo — a foto é a única protagonista visual.

> 🔴 **PATTERN DECORATIVO DE FUNDO:** todo slide (EXCETO a capa) DEVE conter também um Pattern_Decorativo vertical no fundo, ancorado à esquerda. Use a função `background_pattern(patterns, slide_index, slide_type=...)` do helpers.py, que escolhe automaticamente a cor do pattern conforme o tipo de fundo (azul_escuro pra escuro/cta, bege pra claro/sand, roxo pra lavender) e cicla entre as 2 variações (estreita e larga). A capa NUNCA recebe pattern decorativo — a foto é a textura.

> 🔴 **TRANSPARÊNCIA NAS IMAGENS DE FUNDO:** todas as imagens de fundo (`background_icon`, `background_pattern` E `corner_pattern`) DEVEM ser renderizadas com opacidade CSS reduzida — nunca em opacidade full. Isso garante que funcionem como assinatura visual sutil sem competir com o conteúdo. Os valores padrão no `base_css()` são `opacity: 0.07-0.08` para o icon, `opacity: 0.20` para o pattern decorativo e `opacity: 0.18` para o pattern canto. Essa é uma regra absoluta — nenhuma imagem de fundo aparece em opacidade 1.

> 🔴 **PATTERN CANTO NO SUPERIOR DIREITO:** todo slide (EXCETO a capa) DEVE conter também um Pattern_Canto no canto superior direito como elemento decorativo. Use a função `corner_pattern(cantos, slide_type=...)` do helpers.py, que escolhe a cor do canto conforme o tipo de fundo (`azul_claro` para escuro/cta, `azul` para claro, `roxo_escuro` para sand/lavender). O pattern é rotacionado 180° via CSS pra ancorar as formas circulares no canto direito superior. A capa NUNCA recebe pattern_canto.

> 🔴 **FONTE DA PALAVRA SINDICOMPANY:** sempre que a palavra "Sindicompany" (ou "sindicompany", em qualquer caixa) aparecer em qualquer slide do carrossel, ela DEVE ser renderizada com a fonte **Epilogue**. A fonte Provicali do logotipo NUNCA é usada no HTML — ela existe apenas no PNG do logo. Como Epilogue é a única fonte da skill (carregada via `build_font_faces()`), essa regra é automaticamente satisfeita desde que nenhum fallback de sistema seja invocado. Verifique sempre que a palavra esteja em elementos com `font-family: 'Epilogue'` herdada do `base_css()`.

> 🔴 **LEGENDA OBRIGATÓRIA + HUMANIZER:** todo carrossel DEVE ser entregue com uma legenda de Instagram pronta no final do HTML. A legenda DEVE OBRIGATORIAMENTE passar pela skill `humanizer` (`/mnt/skills/user/humanizer/SKILL.md`) ANTES de ser finalizada — sem exceção. O processo é: (1) escrever draft inicial da legenda, (2) rodar o humanizer pra eliminar AI tells (rule of three, gerúndio decorativo, traços, vocabulário promocional, parallelisms, hedging excessivo, emojis decorativos, conclusões genéricas), (3) fazer o audit final ("o que ainda soa AI?") e revisar, (4) só então embutir a legenda no HTML via `wrap_html()`. Nunca entregar legenda sem ter passado pelo humanizer.

> 🔴 **LEGENDA NA RESPOSTA DO CHAT:** toda legenda gerada DEVE ser enviada como texto plano na mensagem de chat de resposta ao usuário, não apenas embutida no HTML. A legenda aparece no HTML como referência visual, mas é OBRIGATÓRIO enviá-la também em texto puro na mensagem final, pronta pra ser copiada e colada no Instagram sem precisar abrir o HTML. Formato: parágrafos separados por linha em branco, hashtags na última linha.

---

## SETUP

Os assets já vêm processados em `assets_processed/` junto com a skill. **Não é preciso fazer nada antes do primeiro uso.** Basta colocar a pasta em `/mnt/skills/user/sindicompany-carrossel/` e gerar o primeiro carrossel.

Se os assets do projeto (`/mnt/project/`) forem atualizados e você quiser re-processar, rode:

```bash
python3 /mnt/skills/user/sindicompany-carrossel/scripts/process_assets.py
```

Isso regenera `assets_processed/` a partir de `/mnt/project/`. Roda em ~5 segundos.

---

## IDENTIDADE DA MARCA

```
NOME:    Sindicompany | "sindicompany" em caixa baixa | "Sindicompany" em início de frase
HANDLE:  @sindicompanybr
TAGLINE: Por mais lares.
PUBLICO: Moradores de condomínio + quem quer contratar síndico profissional
TOM:     Alegre · Amigável · Objetivo · Transparente
```

### Paleta

```
Onix      #1A1C29   fundo escuro, texto principal
Sand      #DABDA9   destaque quente
Mint      #84C7D3   accent, CTAs, destaques frescos
Lavender  #B8C0FF   fundo suave, apoio
White     #FFFFFF
Gray 5    #F4F4F5   fundo claro
```

Combos preferenciais: **Onix + Mint**, **Onix + Sand**, **Sand + Mint**. Lavender como apoio.

### Tipografia — Epilogue (exclusiva)

Epilogue é a **única** fonte dos carrosséis. Provicali é do logotipo, nunca aparece no HTML.

**As fontes estão embutidas em `assets/fonts/` como woff2.** O helper `build_font_faces()` gera o `@font-face` com base64. **Nunca usar `@import` do Google Fonts** — o ambiente de render pode não ter rede no momento do screenshot, e a fonte cai pra fallback.

| Papel | Peso | Tamanho | Uso |
|-------|------|---------|-----|
| Título capa | Black (900) | 78px | Headline do slide 1 |
| Título slide | ExtraBold (800) | 72–80px | Título dos slides internos |
| Texto principal | SemiBold (600) | 42–50px | Corpo, argumentos |
| Texto secundário | Regular (400) | 30–38px | Apoio, contexto |
| Badge | Bold (700) | 20–26px | Labels uppercase |
| Número de lista | Black (900) | 60–70px | Listas numeradas |

---

## FLUXO DE TRABALHO

```
1. PASSO 0: Perguntar tema, objetivo e formato
2. PASSO 1: Escrever copy (humanizer ON)
3. PASSO 2: Construir build script usando helpers.py
4. PASSO 3: Rodar render_4k.py para gerar PNGs
5. PASSO 4: Entregar PNGs + HTML + legenda via present_files
```

### PASSO 0 — Perguntar o tema

Use `ask_user_input_v0` se possível:

**Tema:**
```
1. Direitos do morador        7. Assembleias e votações
2. Taxa de condomínio          8. Valorização do imóvel
3. Síndico profissional        9. Tecnologia no condomínio
4. Conflitos entre vizinhos   10. Tendências em alta (web search)
5. Segurança                  11. Outro
6. Animais de estimação
```

**Formato:**
```
A. História real        E. Dado que choca
B. Lista                F. Tutorial rápido
C. Mito vs Verdade      G. Opinião forte
D. Antes/Depois
```

**História real é o formato que mais engaja e salva.** Sempre ofereça como primeira opção quando o tema permitir.

### PASSO 1 — Copy (com humanizer)

**Regras de copy:**
- Frases curtas. Uma ideia por slide. Leitura em <3 segundos.
- Slide 1 decide tudo. Curiosidade em 1,5 segundo ou o post morreu.
- Fale pra uma pessoa. "Você", não "os moradores".
- Crie tensão que só resolve no próximo slide.
- Slide final: pergunta fácil (SIM/NÃO).

**Lista negra (nunca usar):**
- "marca um momento crucial", "papel fundamental", "cenário em constante evolução"
- "vibrante", "profundo", "inovador", "revolucionário", "transformador"
- "destacando a importância de…", "reforçando o compromisso com…"
- "especialistas afirmam", "estudos mostram"
- "o futuro é promissor", "juntos somos mais fortes"
- **TRAÇO (—): PROIBIDO.** Substituir por ponto, vírgula ou dois-pontos.

**Teste antes de finalizar cada slide:** "Consigo ler em menos de 3 segundos e entender?" Se não, cortar.

**Humanizer rules:**
- Situação real, não conceito (*"Você já pediu pra ver a conta do condomínio?"*, não *"A transparência é fundamental"*)
- Reaja, não só reporte (*"Você paga todo mês. Tem direito. Quase ninguém sabe."*)
- Seja específico (*"7 em cada 10 condomínios…"*, não *"muitos condomínios…"*)
- Varie o ritmo (frases longas e curtas)
- Deixe imperfeição natural

### PASSO 2 — Build script

Estrutura de um script de build típico:

```python
#!/usr/bin/env python3
"""Build: Carrossel [TEMA]"""
import sys, os, base64
sys.path.insert(0, '/mnt/skills/user/sindicompany-carrossel/scripts')
from helpers import (
    asset_b64, load_logos, load_all_icons, build_font_faces,
    dots, header, wrap_html, background_icon
)

OUT = '/mnt/user-data/outputs/carrossel_[tema_slug].html'

logos = load_logos()
all_icons = load_all_icons()  # os 6 icons pra regra do icon de fundo
fonts_css = build_font_faces()

# Imagem da capa (sempre peça ao usuário para enviar a foto).
UPLOAD = '/mnt/user-data/uploads/[nome_arquivo_do_usuario].png'
with open(UPLOAD, 'rb') as f:
    imagem_capa_b64 = 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

TOTAL = 6  # ajustar ao número de slides

# Slide 1 — CAPA (foto + texto na metade de baixo)
# REGRA: background_icon() sempre antes do conteúdo
slide1 = f'''
<div class="slide capa">
  <img src="{imagem_capa_b64}" class="hero-img" alt="">
  <div class="hero-overlay"></div>
  {background_icon(all_icons, 0)}
  {header(logos, on_dark=True)}
  <div class="slide-content capa-content">
    <span class="badge-capa">HISTÓRIA REAL</span>
    <h1 class="titulo-capa">Gancho forte.<br><span class="hl-mint">Palavra-chave</span> em destaque.</h1>
  </div>
  {dots(0, TOTAL)}
</div>
'''

# Slide 2 — Onix (slide escuro, light_bg=False)
slide2 = f'''
<div class="slide escuro">
  {background_icon(all_icons, 1)}
  {header(logos, on_dark=True)}
  <div class="slide-content padded">
    <span class="badge">CAPÍTULO 1</span>
    <h2 class="titulo-slide">Título em <span class="hl-sand">destaque sand</span>.</h2>
    <p class="texto-principal">Frase de impacto curta.</p>
  </div>
  {dots(1, TOTAL)}
</div>
'''

# Slide 3 — Claro (Gray-5, light_bg=True para o icon ficar escuro)
slide3 = f'''
<div class="slide claro">
  {background_icon(all_icons, 2, light_bg=True)}
  {header(logos, on_dark=False)}
  <div class="slide-content padded">
    <span class="badge dark">CAPÍTULO 2</span>
    <h2 class="titulo-slide dark">Título em onix.</h2>
    <p class="texto-principal dark">Corpo em onix sobre gray-5.</p>
  </div>
  {dots(2, TOTAL)}
</div>
'''

# Slide 4 — Sand (momento emocional, light_bg=True)
slide4 = f'''
<div class="slide sand">
  {background_icon(all_icons, 3, light_bg=True)}
  {header(logos, on_dark=False)}
  <div class="slide-content padded">
    <span class="badge dark">CAPÍTULO 3</span>
    <h2 class="titulo-slide dark">Clímax emocional.</h2>
  </div>
  {dots(3, TOTAL)}
</div>
'''

# Slide 5 — Virada / Lista numerada (escuro)
slide5 = f'''
<div class="slide escuro">
  {background_icon(all_icons, 4)}
  {header(logos, on_dark=True)}
  <div class="slide-content padded">
    <span class="badge">A VIRADA</span>
    <h2 class="titulo-slide">Sem X.<br><span class="hl-mint">Com Y.</span></h2>
    <ul class="lista-acoes">
      <li><span class="num">1</span><div><strong>Primeira ação</strong>.</div></li>
      <li><span class="num">2</span><div><strong>Segunda ação</strong>.</div></li>
      <li><span class="num">3</span><div><strong>Terceira ação</strong>.</div></li>
    </ul>
  </div>
  {dots(4, TOTAL)}
</div>
'''

# Slide 6 — CTA final
slide6 = f'''
<div class="slide cta">
  {background_icon(all_icons, 5)}
  {header(logos, on_dark=True)}
  <div class="slide-content cta-content">
    <span class="cta-marca">sindicompany</span>
    <h2 class="titulo-cta">Fecho emocional.</h2>
    <div class="pergunta-box">
      <p class="pergunta">Pergunta de engajamento?</p>
      <p class="pergunta-sub">Comenta <strong>SIM</strong> ou <strong>NÃO</strong>.</p>
    </div>
    <p class="tagline">Por mais lares.</p>
  </div>
  {dots(5, TOTAL)}
</div>
'''

LEGENDA = """Gancho curto. Mesma energia do slide 1.

Dois a três parágrafos curtos de contexto.

Pergunta de engajamento, mesma do CTA.

Por mais lares. 🏡

#sindicompany #gestaodecondominios #sindicoprofissional #condominio
[+3–5 hashtags específicas do tema]"""

html = wrap_html([slide1, slide2, slide3, slide4, slide5, slide6], fonts_css, LEGENDA)

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'OK -> {OUT}')
```

### PASSO 3 — Render 4K

```bash
python3 /mnt/skills/user/sindicompany-carrossel/scripts/render_4k.py \
    /mnt/user-data/outputs/carrossel_[tema].html \
    /mnt/user-data/outputs \
    carrossel_[tema]
```

Gera `carrossel_[tema]_01.png` até `carrossel_[tema]_NN.png`, cada um em 3072×3839.

### PASSO 4 — Entregar

Use `present_files` com a lista dos PNGs + HTML. O HTML é entregue junto como backup e fonte fiel editável.

---

## IMAGEM DA CAPA (ponto importante)

O ambiente **não tem acesso confiável a bancos de imagem**: Unsplash está atrás de challenge anti-bot (Anubis), Pexels/Bing/Google bloqueiam sem JS. Tentar hashes do Unsplash às cegas resulta em fotos erradas.

**Política:**
1. **Sempre pergunte ao usuário** qual imagem quer na capa antes de construir o HTML.
2. Peça pra ele arrastar o arquivo no chat. O upload vai pra `/mnt/user-data/uploads/`.
3. Se o usuário não tiver uma imagem específica em mente, sugira:
    - Baixar do Unsplash/Pexels fora do Claude e subir
    - Usar uma foto do banco interno dele
4. **Nunca invente hashes de Unsplash.** Se precisar insistir, use `image_search` para consultar visualmente, mas os resultados não expõem URLs ao Claude — só ao usuário.

---

## TIPOS DE SLIDE (quick reference)

Cada tipo aplica a classe base correspondente.

| Classe | Fundo | Header logo | Uso |
|--------|-------|-------------|-----|
| `.capa` | Foto + overlay onix | LOGO_CLARO | Sempre o slide 1 |
| `.escuro` | Onix | LOGO_CLARO | Slides de impacto, listas, dados |
| `.claro` | Gray-5 | LOGO_ESCURO | Contraste, respiros |
| `.sand` | Sand | LOGO_ESCURO | Slides emocionais, clímax |
| `.lavender` | Lavender | LOGO_ESCURO | Apoio, variação |
| `.cta` | Onix | LOGO_CLARO | Sempre o último, com pergunta + tagline |

**Alternância recomendada:** Capa → Escuro → Claro → Sand → Escuro → CTA. Nunca 3 slides do mesmo tom seguidos.

### Regra da capa (reforço)

```css
.capa-content{
  position:absolute;top:50%;left:0;right:0;bottom:0;
  /* texto só na metade de baixo, foto livre em cima */
}
```

Se o título estiver muito longo pra caber em 50%, reduzir o font-size ou encurtar o copy. **Nunca deixe o texto invadir a metade de cima.**

---

## PATTERNS E ICONS (opcionais, com cuidado)

Após `process_assets.py`, os patterns têm alpha channel real e funcionam sem `mix-blend-mode`.

**O que funciona bem:**
- `pattern-lateral` (esquerdo/direito) em slides escuros e claros com `opacity: 0.16–0.20`
- `icon-marca` no canto inferior direito de slides com espaço sobrando

**O que não funciona bem (evitar):**
- `pattern-canto` recortado em canto — o recorte mostra um bracket estranho
- Pattern em slide 5 (lista numerada) — compete visualmente com os números
- Múltiplos elementos decorativos no mesmo slide

**Regra prática:** patterns e icons são opcionais. Se o slide já é forte com tipografia + cor, deixa limpo. O skill diz: *"Slides de texto denso ganham mais com respiro do que com pattern."*

**Exemplo de uso correto (lateral em slide escuro):**
```python
from helpers import load_patterns
patterns = load_patterns()

slide_html = f'''
<div class="slide escuro">
  <img src="{patterns['PATTERN_DIR_MINT']}" class="pattern-lateral direito" alt="">
  {header(logos, on_dark=True)}
  <div class="slide-content padded">...</div>
  {dots(1, TOTAL)}
</div>
'''
```

---

## CHECKLIST FINAL (antes de entregar)

- [ ] `assets_processed/` existe e tem os logos
- [ ] Fontes Epilogue embutidas via `build_font_faces()`
- [ ] Slide 1 tem imagem de fundo real
- [ ] Slide 1 texto está APENAS na metade de baixo
- [ ] 🔴 **Todo slide tem `background_icon()` aplicado** (regra inegociável)
- [ ] Slides claros usam `light_bg=True` no background_icon
- [ ] Header bar em todos os slides com logo correto (LOGO_CLARO escuro, LOGO_ESCURO claro)
- [ ] Dots de navegação em todos os slides
- [ ] Uma ideia por slide, leitura em <3 segundos
- [ ] "sindicompany" em caixa baixa onde aparece
- [ ] Slide CTA tem pergunta SIM/NÃO + "Por mais lares."
- [ ] Nenhum traço (—) no copy
- [ ] Passou pelo humanizer (sem lista negra)
- [ ] Legenda Instagram montada no final do HTML
- [ ] PNGs renderizados em 3072×3839
- [ ] Arquivos entregues via `present_files`

---

## ESTRUTURA DA SKILL

```
sindicompany-carrossel/
├── SKILL.md                    (este arquivo)
├── scripts/
│   ├── process_assets.py       (setup único — cria assets_processed/)
│   ├── helpers.py              (asset_b64, build_font_faces, header, dots, wrap_html, base_css)
│   └── render_4k.py            (Playwright → PNG 4K)
├── assets/
│   └── fonts/
│       ├── epilogue-400.woff2
│       ├── epilogue-600.woff2
│       ├── epilogue-700.woff2
│       ├── epilogue-800.woff2
│       └── epilogue-900.woff2
└── assets_processed/           (gerado pelo process_assets.py)
    ├── Logotipo_Sindicompany_5.png   (LOGO_CLARO, branco em alpha)
    ├── Logotipo_Sindicompany_6.png   (LOGO_ESCURO, onix em alpha)
    ├── Pattern_*.png                  (todos com alpha)
    └── Logotipo_Sindicompany__Icon_*.png
```

---

## LIÇÕES APRENDIDAS (v1 → v2)

1. **Google Fonts @import é frágil.** A rede pode não estar disponível no momento do render, e a fonte cai pra fallback sans-serif invisível no PNG final. **Solução:** fontes embutidas como base64 direto no CSS.

2. **PNGs do projeto estão em RGB sem alpha.** Tentativa de usar `mix-blend-mode: multiply/screen` funciona parcialmente mas quebra em slides claros (fundo preto do PNG vira box escuro). **Solução:** processar com Pillow pra adicionar alpha channel baseado em luminância.

3. **LOGO_ESCURO original é onix-sobre-preto.** Luminância não separa os dois. **Solução:** derivar do LOGO_CLARO (branco-sobre-preto) e recolorir pra onix.

4. **Texto da capa invadindo a foto desperdiça o impacto emocional.** **Solução:** texto SEMPRE na metade de baixo, com overlay gradient cobrindo só essa metade.

5. **Unsplash e bancos de imagem estão bloqueados no ambiente de execução.** **Solução:** pedir upload ao usuário, nunca adivinhar hashes.

6. **Pattern_Canto recortado gera formas estranhas (brackets).** **Solução:** preferir pattern-lateral ou omitir decoração.

7. **Export em 4K via Playwright com `device_scale_factor=2.844`** dá 3072×3839 perfeito, muito superior a qualquer abordagem PIL de renderização manual de texto.
