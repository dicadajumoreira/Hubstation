"""
Acesso ao Supabase (DB + Storage) usando a service role key.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET = "revistas-pdfs"


def _client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY precisam estar setados",
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def fetch_revista(revista_id: str) -> dict[str, Any] | None:
    sb = _client()
    res = (
        sb.table("revistas")
        .select("*")
        .eq("id", revista_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def fetch_editorial(mes: int, ano: int) -> dict[str, Any] | None:
    sb = _client()
    res = (
        sb.table("editoriais_mensais")
        .select("*")
        .eq("mes", mes)
        .eq("ano", ano)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def fetch_condo_meta(condominio: str) -> dict[str, Any] | None:
    sb = _client()
    res = (
        sb.table("condominios_meta")
        .select("*")
        .eq("nome", condominio)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def upload_pdf(revista_id: str, pdf_bytes: bytes) -> str:
    """Sobe o PDF (upsert) e retorna o storage path."""
    sb = _client()
    path = f"{revista_id}.pdf"
    sb.storage.from_(BUCKET).upload(
        path=path,
        file=pdf_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )
    return path


def mark_publicada(revista_id: str, storage_path: str, paginas: int) -> None:
    sb = _client()
    sb.table("revistas").update(
        {
            "status": "publicada",
            "pdf_storage_path": storage_path,
            "paginas": paginas,
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "erro_mensagem": None,
        }
    ).eq("id", revista_id).execute()


def mark_erro(revista_id: str, mensagem: str) -> None:
    sb = _client()
    sb.table("revistas").update(
        {"status": "erro", "erro_mensagem": mensagem},
    ).eq("id", revista_id).execute()
