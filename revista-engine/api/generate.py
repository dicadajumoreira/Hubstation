"""
CLI: `python -m api.generate --revista-id <UUID>`

Roda dentro do GitHub Actions. Busca a revista no Supabase, monta o
PDF, faz upload e marca como publicada. Em caso de erro, marca o
registro como `erro` com a mensagem.

Variáveis de ambiente:
  SUPABASE_URL                 (obrigatória)
  SUPABASE_SERVICE_ROLE_KEY    (obrigatória)
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

# Ajusta sys.path pra rodar como `python -m api.generate`
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.composer import build_inputs_from_db, render_pdf_bytes
from api.supabase_client import (
    fetch_condo_meta,
    fetch_editorial,
    fetch_revista,
    mark_erro,
    mark_publicada,
    upload_pdf,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revista-id", required=True)
    args = ap.parse_args()

    revista_id = args.revista_id

    try:
        print(f"[generate] revista_id={revista_id}", flush=True)
        revista = fetch_revista(revista_id)
        if revista is None:
            print(f"[generate] revista não encontrada", flush=True)
            return 2

        editorial = fetch_editorial(revista["mes"], revista["ano"])
        if editorial is None:
            print(
                f"[generate] WARN editorial faltando pra mes={revista['mes']}/ano={revista['ano']}; "
                "renderizando com sugestões do mês",
                flush=True,
            )
            editorial = {}

        condo = fetch_condo_meta(revista["condominio"])
        if condo is None:
            print(
                f"[generate] WARN condo_meta '{revista['condominio']}' não encontrado; "
                "renderizando com placeholders",
                flush=True,
            )
            condo = {}

        print(
            f"[generate] condo={revista['condominio']} mes={revista['mes']:02d}/{revista['ano']}",
            flush=True,
        )

        sequence = build_inputs_from_db(revista, editorial, condo)
        print(f"[generate] composing {len(sequence)} sections", flush=True)

        pdf_bytes, page_count = render_pdf_bytes(sequence)
        print(f"[generate] PDF rendered: {len(pdf_bytes)//1024}KB · {page_count} pages", flush=True)

        storage_path = upload_pdf(revista_id, pdf_bytes)
        print(f"[generate] uploaded to {storage_path}", flush=True)

        mark_publicada(revista_id, storage_path, page_count)
        print(f"[generate] OK", flush=True)
        return 0

    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        print(f"[generate] ERROR: {e}\n{tb}", flush=True)
        try:
            mark_erro(revista_id, str(e)[:500])
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
