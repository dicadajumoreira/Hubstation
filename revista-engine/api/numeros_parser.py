"""
Parser pra dashboard de prestação de contas.

Dois caminhos de entrada:

1. URL direta de arquivo (preferido) — `prestacao_arquivo_url` aponta pra
   um PNG/JPG/WebP/PDF subido pela editora via form. A engine baixa via
   HTTP, detecta o tipo e roda Vision/OCR.

2. Pasta do Drive (legado) — `drive_prestacao_url`. A engine baixa a
   pasta inteira via gdown, acha o primeiro arquivo suportado dentro.

Formatos suportados:
- .html / .htm  → texto bruto vai pro GPT extrair
- .png .jpg .jpeg .webp .gif  → GPT-4o Vision lê o print
- .pdf  → rasteriza primeira página em PNG via pypdfium2 e manda pra Vision

Retorna o dict no formato esperado pela seção S11 (our_numbers.py):
  - kpis: {receita_brl, despesas_brl, fundo_reserva_brl, inadimplencia_pct}
  - principais_despesas: [{categoria, valor_brl, observacao}]
  - historico: [{mes_label, saldo_brl}]
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from api.drive import extract_folder_id
from api.text_gen import _gerar_json, _gerar_json_vision


_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_HTML_EXTS = {".html", ".htm"}
_PDF_EXTS = {".pdf"}


_PROMPT_INSTRUCAO = (
    "Aqui está o dashboard de prestação de contas mensal de um condomínio "
    "brasileiro. Extraia os números financeiros em JSON estruturado.\n\n"
    "Formato esperado:\n"
    "{\n"
    '  "kpis": {\n'
    '    "saldo_anterior_brl": float,  // saldo no início do período (mês anterior)\n'
    '    "credito_mes_brl": float,     // total de entradas/créditos no mês\n'
    '    "debito_mes_brl": float,      // total de saídas/débitos no mês\n'
    '    "saldo_atual_brl": float      // saldo no fim do período = anterior + credito - debito\n'
    "  },\n"
    '  "resumo_contas": [\n'
    '    {"conta":"Conta corrente", "saldo_brl": float},\n'
    '    {"conta":"Fundo de reserva", "saldo_brl": float},\n'
    '    {"conta":"Aplicação financeira", "saldo_brl": float}\n'
    "    // 2 a 6 contas com saldo final do mês\n"
    "  ],\n"
    '  "previsto_realizado": [\n'
    '    {"categoria":"...", "previsto_brl": float, "realizado_brl": float}\n'
    "    // 4 a 8 categorias macro com previsto vs realizado do mês\n"
    "  ],\n"
    '  "principais_despesas": [\n'
    '    {"categoria":"...", "valor_brl": float, "observacao": "..."}\n'
    "    // 5 a 8 categorias detalhadas das maiores despesas (Despesas por categoria)\n"
    "  ]\n"
    "}\n\n"
    "REGRAS:\n"
    "- Use float (R$ 12.345,67 → 12345.67). Não use string nem prefixo R$.\n"
    "- Use 0 quando o valor não estiver claramente disponível.\n"
    "- Em 'previsto_realizado', se não houver coluna 'previsto' no dashboard, "
    "  retorne o array vazio []. Não invente valores.\n"
    "- Em 'resumo_contas', use os nomes das contas exatamente como aparecem.\n"
    "- 'principais_despesas' lista as MAIORES despesas (categoria detalhada, não macro).\n"
    "- Sem texto fora do JSON. Sem markdown.\n"
)


_FALLBACK = {
    "kpis": {
        "saldo_anterior_brl": 0,
        "credito_mes_brl": 0,
        "debito_mes_brl": 0,
        "saldo_atual_brl": 0,
    },
    "resumo_contas": [],
    "previsto_realizado": [],
    "principais_despesas": [],
}


# =============================================================================
# Download helpers
# =============================================================================

def _baixar_pasta_drive(drive_url: str, dest: Path) -> Path | None:
    folder_id = extract_folder_id(drive_url)
    if not folder_id:
        print(f"[numeros] URL de Drive inválida: {drive_url}", flush=True)
        return None
    dest.mkdir(parents=True, exist_ok=True)
    print(f"[numeros] baixando pasta Drive {folder_id}", flush=True)
    try:
        import gdown  # noqa: PLC0415
        gdown.download_folder(
            url=f"https://drive.google.com/drive/folders/{folder_id}",
            output=str(dest),
            quiet=False,
            use_cookies=False,
            remaining_ok=True,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[numeros] download da pasta falhou: {type(e).__name__}: {e}", flush=True)
        return None
    return dest


def _baixar_arquivo_direto(file_url: str, dest: Path) -> Path | None:
    """Baixa um único arquivo (PNG/JPG/PDF) de uma URL HTTP(S) pública."""
    dest.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlparse(file_url)
    nome = Path(parsed.path).name or "arquivo.bin"
    out = dest / nome
    print(f"[numeros] baixando arquivo direto {file_url}", flush=True)
    try:
        req = urllib.request.Request(file_url, headers={"User-Agent": "revista-engine/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        # Se a URL não tem extensão útil, deduz pelo content-type
        if out.suffix.lower() not in _IMAGE_EXTS | _PDF_EXTS | _HTML_EXTS:
            ext_por_tipo = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "application/pdf": ".pdf",
                "text/html": ".html",
            }.get(ctype)
            if ext_por_tipo:
                out = out.with_suffix(ext_por_tipo)
        out.write_bytes(data)
        print(f"[numeros] arquivo salvo em {out.name} ({len(data)} bytes, ctype={ctype})", flush=True)
        return out
    except Exception as e:  # noqa: BLE001
        print(f"[numeros] download direto falhou: {type(e).__name__}: {e}", flush=True)
        return None


def _localizar_arquivos(dest: Path) -> dict[str, list[Path]]:
    """Devolve {htmls, imagens, pdfs} encontrados na pasta."""
    htmls: list[Path] = []
    imagens: list[Path] = []
    pdfs: list[Path] = []
    for f in dest.rglob("*"):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in _HTML_EXTS:
            htmls.append(f)
        elif ext in _IMAGE_EXTS:
            imagens.append(f)
        elif ext in _PDF_EXTS:
            pdfs.append(f)
    return {"htmls": htmls, "imagens": imagens, "pdfs": pdfs}


# =============================================================================
# Conversores
# =============================================================================

def _strip_html(html: str, max_chars: int = 30000) -> str:
    html = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    html = re.sub(r"<svg\b.*?</svg>", "", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"<img\b[^>]*>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"\s+", " ", html)
    if len(html) > max_chars:
        html = html[:max_chars]
    return html


def _pdf_para_imagens(pdf_path: Path, dest_dir: Path, max_pages: int = 3) -> list[Path]:
    """Rasteriza as primeiras páginas do PDF em PNG. Retorna lista de paths."""
    try:
        import pypdfium2 as pdfium  # noqa: PLC0415
    except Exception as e:  # noqa: BLE001
        print(f"[numeros] pypdfium2 indisponível: {e}", flush=True)
        return []
    out_paths: list[Path] = []
    try:
        doc = pdfium.PdfDocument(str(pdf_path))
        n = min(len(doc), max_pages)
        # 200 DPI é o suficiente pra OCR sem inflar o payload
        scale = 200 / 72
        for i in range(n):
            page = doc[i]
            img = page.render(scale=scale).to_pil()
            out = dest_dir / f"{pdf_path.stem}-p{i+1}.png"
            img.save(out, format="PNG", optimize=True)
            out_paths.append(out)
        print(f"[numeros] PDF '{pdf_path.name}' rasterizado em {len(out_paths)} página(s)", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[numeros] falha rasterizando PDF: {type(e).__name__}: {e}", flush=True)
    return out_paths


# =============================================================================
# Pipeline
# =============================================================================

def _processar_arquivos(achados: dict[str, list[Path]], dest: Path) -> dict[str, Any] | None:
    """Dado {htmls, imagens, pdfs} em ordem de prioridade, extrai KPIs."""
    imagens = list(achados.get("imagens") or [])
    pdfs = list(achados.get("pdfs") or [])
    htmls = list(achados.get("htmls") or [])

    # Se tem PDF, converte primeiras páginas em PNG e mistura com imagens
    if pdfs:
        for pdf in sorted(pdfs, key=lambda p: p.name)[:1]:  # 1 PDF por vez
            imagens.extend(_pdf_para_imagens(pdf, dest))

    if imagens:
        imgs = sorted(imagens, key=lambda p: p.name)[:3]
        print(f"[numeros] processando via Vision: {[p.name for p in imgs]}", flush=True)
        return _gerar_json_vision(
            _PROMPT_INSTRUCAO,
            [str(p) for p in imgs],
            _FALLBACK,
            expected_keys=["kpis"],
        )

    if htmls:
        try:
            raw_html = htmls[0].read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            print(f"[numeros] erro lendo {htmls[0].name}: {e}", flush=True)
            return None
        snippet = _strip_html(raw_html)
        print(f"[numeros] HTML reduzido para {len(snippet)} chars", flush=True)
        prompt = _PROMPT_INSTRUCAO + "\nHTML:\n" + snippet
        return _gerar_json(prompt, _FALLBACK, expected_keys=["kpis"])

    print(f"[numeros] nenhum arquivo suportado em {dest}", flush=True)
    return None


def parse_nossos_numeros_arquivo(file_url: str, dest: Path) -> dict[str, Any] | None:
    """Versão preferida: baixa um único arquivo (PNG/JPG/WebP/PDF) por URL direta."""
    arquivo = _baixar_arquivo_direto(file_url, dest)
    if not arquivo:
        return None
    ext = arquivo.suffix.lower()
    achados: dict[str, list[Path]] = {"htmls": [], "imagens": [], "pdfs": []}
    if ext in _IMAGE_EXTS:
        achados["imagens"] = [arquivo]
    elif ext in _PDF_EXTS:
        achados["pdfs"] = [arquivo]
    elif ext in _HTML_EXTS:
        achados["htmls"] = [arquivo]
    else:
        print(f"[numeros] extensão '{ext}' não suportada", flush=True)
        return None
    return _processar_arquivos(achados, dest)


def parse_nossos_numeros(drive_url: str, dest: Path) -> dict[str, Any] | None:
    """Legado: baixa pasta do Drive e procura arquivo suportado dentro."""
    if not _baixar_pasta_drive(drive_url, dest):
        return None
    achados = _localizar_arquivos(dest)
    print(
        f"[numeros] encontrados: {len(achados['htmls'])} HTML + "
        f"{len(achados['imagens'])} imagem(ns) + {len(achados['pdfs'])} PDF(s)",
        flush=True,
    )
    return _processar_arquivos(achados, dest)
