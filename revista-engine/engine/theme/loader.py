"""
Theme loader — lê tema-*.yaml e produz um objeto Theme que sabe gerar
o CSS necessário para renderizar uma seção (paleta + @font-face + logos).

A engine de render (Playwright) recebe HTML auto-contido, então precisamos
embutir as fontes (data: URLs) e os SVGs dos logos diretamente no HTML.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FontFile:
    """Um arquivo de fonte declarado no tema."""

    weight: str          # "400", "100 900" (variable), etc.
    style: str           # "normal" | "italic"
    file: Path           # caminho absoluto resolvido
    format: str          # "opentype" | "woff2-variations" | "woff2"


@dataclass
class FontFamily:
    family: str
    files: list[FontFile] = field(default_factory=list)


@dataclass
class Theme:
    """
    Tema carregado e resolvido. Todos os caminhos são absolutos.
    Encapsula tudo que uma seção precisa para renderizar.
    """

    nome: str
    handle: str
    tagline: str
    paleta: dict[str, str]
    fonte_titulos: FontFamily
    fonte_corpo: FontFamily
    logo_paths: dict[str, Path]   # 'mono' | 'color' | 'white' -> Path
    base_dir: Path                # diretório do tema (pra resolver paths)

    # =========================================================================
    # Geração de CSS
    # =========================================================================

    def palette_css_vars(self) -> str:
        """Retorna :root { --onix: ...; --sand: ...; } pra usar em qualquer CSS."""
        lines = [":root {"]
        for name, value in self.paleta.items():
            lines.append(f"  --{name.replace('_', '-')}: {value};")
        lines.append("}")
        return "\n".join(lines)

    def font_face_css(self) -> str:
        """
        Retorna @font-face declarations com as fontes embutidas como data: URLs.

        Embutir é proposital: o HTML resultante é auto-contido e pode ser
        renderizado por Playwright sem precisar resolver assets externos.
        Custo: ~250KB extras no HTML (irrelevante para PDF).
        """
        blocks = []
        for fam in (self.fonte_titulos, self.fonte_corpo):
            for f in fam.files:
                data_url = self._file_to_data_url(f.file)
                fmt = f"format('{f.format}')"
                blocks.append(
                    f"@font-face {{\n"
                    f"  font-family: '{fam.family}';\n"
                    f"  font-weight: {f.weight};\n"
                    f"  font-style: {f.style};\n"
                    f"  font-display: swap;\n"
                    f"  src: url({data_url}) {fmt};\n"
                    f"}}"
                )
        return "\n".join(blocks)

    def background_patterns_css(self) -> str:
        """CSS de regras nth-child que aplicam um pattern diferente em
        cada página. A regra base (::before com opacity 0.06) já vem
        do page_document — esta função só preenche o background-image
        ciclando entre os patterns disponíveis.

        Procura nesta ordem:
          1. Arquivos locais em engine/theme/patterns/pattern-N.{ext}
             (commitados no repo) → embute como data URI base64
          2. Bucket público do Supabase em __patterns/pattern-N.{ext}
             → baixa via HTTP e embute como data URI

        Se nada for encontrado, devolve string vazia (no-op).
        """
        encontrados_data_urls: list[str] = []

        # Caminho 1: arquivos locais commitados no repo
        anchor = next(iter(self.logo_paths.values()), None) if hasattr(self, "logo_paths") else None
        patterns_dir = anchor.parent.parent / "patterns" if anchor else None
        suportados = (".png", ".jpg", ".jpeg", ".webp", ".svg")

        local_paths: dict[int, Path] = {}
        if patterns_dir and patterns_dir.exists():
            for i in range(1, 21):
                for ext in suportados:
                    p = patterns_dir / f"pattern-{i}{ext}"
                    if p.exists():
                        local_paths[i] = p
                        break

        # Caminho 2: Supabase Storage (bucket público condominios-fotos,
        # prefix __patterns/). Tenta cada slot 1..10 com extensões comuns.
        # Só tenta se SUPABASE_URL estiver setada.
        supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        remote_data_urls: dict[int, str] = {}
        if supabase_url:
            import urllib.error
            import urllib.request
            for i in range(1, 21):
                if i in local_paths:
                    continue  # já tem local, pula remoto
                for ext in (".png", ".jpg", ".jpeg", ".webp"):
                    url = (
                        f"{supabase_url}/storage/v1/object/public/"
                        f"condominios-fotos/__patterns/pattern-{i}{ext}"
                    )
                    try:
                        req = urllib.request.Request(
                            url,
                            headers={"User-Agent": "revista-engine/1.0"},
                        )
                        with urllib.request.urlopen(req, timeout=15) as resp:
                            if resp.status != 200:
                                continue
                            content = resp.read()
                            ctype = resp.headers.get(
                                "Content-Type", "image/png"
                            ).split(";")[0].strip()
                        b64 = base64.b64encode(content).decode("ascii")
                        remote_data_urls[i] = f"data:{ctype};base64,{b64}"
                        break  # encontrou nessa extensão
                    except urllib.error.HTTPError:
                        continue  # 404 ou outro — tenta próxima ext
                    except Exception as e:  # noqa: BLE001
                        print(
                            f"[theme] pattern {i}{ext} falhou: {type(e).__name__}: {e}",
                            flush=True,
                        )
                        break

        # Consolida em ordem 1..10, descartando slots vazios
        for i in range(1, 21):
            if i in local_paths:
                encontrados_data_urls.append(self._image_to_data_url(local_paths[i]))
            elif i in remote_data_urls:
                encontrados_data_urls.append(remote_data_urls[i])

        if not encontrados_data_urls:
            return ""

        n = len(encontrados_data_urls)
        sel_base = ".page"
        regras: list[str] = []
        for i, data_url in enumerate(encontrados_data_urls, start=1):
            regras.append(
                f"{sel_base}:nth-child({n}n+{i})::before {{ "
                f"background-image: url('{data_url}'); }}"
            )
        return "\n".join(regras)

    def _image_to_data_url(self, path: Path) -> str:
        mime = {
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".svg":  "image/svg+xml",
        }.get(path.suffix.lower(), "application/octet-stream")
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"

    def logo_svg(self, variant: str = "white") -> str:
        """
        Retorna o conteúdo SVG do logo, pronto para embutir inline no HTML.
        variant: 'mono' | 'color' | 'white'.
        """
        if variant not in self.logo_paths:
            raise ValueError(
                f"Variante de logo '{variant}' não existe no tema. "
                f"Disponíveis: {list(self.logo_paths)}"
            )
        return self.logo_paths[variant].read_text(encoding="utf-8")

    def page_document(
        self,
        body: str,
        *,
        format: str = "a4",
        extra_css: str = "",
    ) -> str:
        """
        Empacota um body HTML num documento completo, com paleta + fontes
        + reset CSS + dimensões da página. Pronto para ir pro Playwright.
        """
        if format == "a4":
            page_w, page_h = 794, 1123
        elif format == "mobile":
            page_w, page_h = 540, 960
        else:
            raise ValueError(f"Format desconhecido: {format!r} (esperado 'a4' | 'mobile')")

        # SVG do logo "mono" (preto sobre fundo claro) embutido como
        # data URI pra usar no rodapé de cada página interna.
        try:
            from urllib.parse import quote as _urlquote
            _logo_raw = self.logo_svg("mono")
            footer_logo_data_uri = _urlquote(_logo_raw, safe="")
        except Exception:
            footer_logo_data_uri = ""

        return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>{self.nome} — preview</title>
<style>
{self.font_face_css()}

{self.palette_css_vars()}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

html, body {{
  background: #2a2a2a;
  font-family: '{self.fonte_corpo.family}', -apple-system, sans-serif;
  color: var(--onix);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}

.page {{
  width: {page_w}px;
  height: {page_h}px;
  margin: 24px auto;
  background: var(--white);
  overflow: hidden;
  position: relative;
  page-break-after: always;
  page-break-inside: avoid;
  box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}}

/* Logo Sindicompany no canto inferior direito de cada pagina interna:
   REMOVIDO a pedido. Capa, contracapa e abertura do caderno ja nao
   tinham; agora as paginas internas tambem nao tem. */
.page:not(.cover-page):not(.back-cover):not(.maint-cover-page)::after {{
  content: none;
}}

/* Padrões geométricos sutis no fundo de TODAS as páginas (opacity ~6%).
   Aplicado também em capa, contracapa, abertura do caderno e hero de
   evento. Como está em ::before com opacity baixa, não compete com
   fotos full-bleed. */
.page::before {{
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  opacity: 0.04;
  pointer-events: none;
  z-index: 0;
}}

{self.background_patterns_css()}

@page {{
  size: {page_w}px {page_h}px;
  margin: 0;
}}

@media print {{
  html, body {{ background: var(--white); }}
  .page {{ margin: 0; box-shadow: none; }}
}}

{extra_css}
</style>
</head>
<body>
{body}
</body>
</html>
"""

    # =========================================================================
    # Helpers internos
    # =========================================================================

    def _file_to_data_url(self, path: Path) -> str:
        mime = {
            ".otf":   "font/otf",
            ".ttf":   "font/ttf",
            ".woff":  "font/woff",
            ".woff2": "font/woff2",
        }.get(path.suffix.lower(), "application/octet-stream")
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"


# =============================================================================
# Loader
# =============================================================================

def load_theme(path: Optional[Path] = None) -> Theme:
    """
    Carrega um tema-*.yaml e devolve um Theme pronto.

    path: caminho do arquivo .yaml. Default = tema-sindicompany.yaml ao lado
          deste módulo.
    """
    if path is None:
        path = Path(__file__).parent / "tema-sindicompany.yaml"
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Tema não encontrado: {path}")

    data = _load_yaml(path)
    base_dir = path.parent

    identidade = data.get("identidade", {})
    paleta = data.get("paleta", {})
    tipo = data.get("tipografia", {})
    logos = data.get("logos", {})

    def parse_family(key: str) -> FontFamily:
        spec = tipo.get(key, {})
        files = []
        for f in spec.get("files", []):
            files.append(FontFile(
                weight=str(f.get("weight", "400")),
                style=f.get("style", "normal"),
                file=(base_dir / f["file"]).resolve(),
                format=f.get("format", "woff2"),
            ))
        return FontFamily(family=spec.get("family", key), files=files)

    return Theme(
        nome=identidade.get("nome", ""),
        handle=identidade.get("handle", ""),
        tagline=identidade.get("tagline", ""),
        paleta={k: v for k, v in paleta.items()},
        fonte_titulos=parse_family("titulos"),
        fonte_corpo=parse_family("corpo"),
        logo_paths={
            k: (base_dir / v).resolve()
            for k, v in logos.items()
        },
        base_dir=base_dir,
    )


def _load_yaml(path: Path) -> dict:
    """
    Tenta importar pyyaml. Se não tiver, faz parse manual mínimo do nosso
    formato específico (não-genérico, só funciona pra tema-*.yaml).
    """
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:
        return _parse_yaml_minimal(path.read_text(encoding="utf-8"))


def _parse_yaml_minimal(text: str) -> dict:
    """
    Parser simplificado: lida com aninhamento por indentação de 2 espaços,
    valores escalares e listas inline {chave: valor, ...}. Não suporta
    referências, anchors ou multilinha.

    É o suficiente para tema-sindicompany.yaml. Se o tema crescer e precisar
    de YAML mais sofisticado, instale pyyaml (já está no requirements.txt).
    """
    result: dict = {}
    stack: list[tuple[int, dict | list]] = [(-1, result)]

    for raw_line in text.splitlines():
        # Strip comentários
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        # Sai de níveis mais profundos
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            stack = [(-1, result)]
        parent = stack[-1][1]

        if content.startswith("- "):
            value = content[2:].strip()
            parsed = _parse_value(value)
            if isinstance(parent, list):
                parent.append(parsed)
            continue

        if ":" not in content:
            continue
        key, _, value = content.partition(":")
        key = key.strip()
        value = value.strip()

        if not value:
            # Pode ser dict aninhado ou lista
            new_container: dict | list = {}
            if isinstance(parent, dict):
                # Olha próxima linha não-vazia pra decidir dict vs list
                # (heurística simples — assume dict por padrão; viramos lista
                # quando uma linha "- ..." aparecer com indent maior)
                parent[key] = new_container
                stack.append((indent, new_container))
            continue

        parsed = _parse_value(value)
        if isinstance(parent, dict):
            # Se a value tiver lista inline, transforma
            parent[key] = parsed

    # Pós-processamento: conserta containers que ganharam itens "- " (deveriam ser listas)
    _fix_lists(result)
    return result


def _parse_value(raw: str):
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    if raw.startswith("{") and raw.endswith("}"):
        # inline dict: { weight: 400, file: x.ttf, ... }
        inner = raw[1:-1]
        out = {}
        for part in _split_inline(inner):
            if ":" not in part:
                continue
            k, _, v = part.partition(":")
            out[k.strip()] = _parse_value(v)
        return out
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1]
        return [_parse_value(p) for p in _split_inline(inner) if p.strip()]
    # Tenta número
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        pass
    return raw


def _split_inline(s: str) -> list[str]:
    """Divide por vírgula respeitando chaves/colchetes/aspas."""
    out, buf, depth = [], [], 0
    in_str = None
    for c in s:
        if in_str:
            buf.append(c)
            if c == in_str:
                in_str = None
            continue
        if c in ('"', "'"):
            in_str = c
            buf.append(c)
            continue
        if c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
        if c == "," and depth == 0:
            out.append("".join(buf).strip())
            buf = []
            continue
        buf.append(c)
    if buf:
        out.append("".join(buf).strip())
    return out


def _fix_lists(node):
    """
    Após o parse minimal, alguns dicts deveriam ter sido listas. Detecta
    pela presença exclusiva de chaves vazias / pelo fato de não haver
    sentido nas chaves. Não-genérico — não faz nada se já estiver ok.
    """
    if isinstance(node, dict):
        for v in node.values():
            _fix_lists(v)
    elif isinstance(node, list):
        for v in node:
            _fix_lists(v)
