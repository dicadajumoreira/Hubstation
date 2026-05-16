/**
 * Webhook de status da geração da revista.
 *
 * O serviço Python (engine) chama PATCH neste endpoint quando termina:
 *
 *   PATCH /api/sindicompany/revista/{id}
 *   Authorization: Bearer <SINDICOMPANY_ENGINE_TOKEN>
 *   Body: { status: "publicada" | "erro", paginas?: int, mensagem?: string }
 *
 * Para "publicada", a engine deve fazer upload do PDF em
 * `revistas-pdfs/{id}.pdf` ANTES de chamar este endpoint.
 */

import { NextRequest, NextResponse } from "next/server";
import {
  getRevista,
  markRevistaErro,
  markRevistaPublished,
} from "@/lib/sindicompany/db";

function unauthorized() {
  return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const expected = process.env.SINDICOMPANY_ENGINE_TOKEN;
  if (!expected) {
    return NextResponse.json(
      { error: "SINDICOMPANY_ENGINE_TOKEN não configurado no servidor" },
      { status: 503 },
    );
  }

  const auth = req.headers.get("authorization") || "";
  if (auth !== `Bearer ${expected}`) {
    return unauthorized();
  }

  const { id } = await params;

  let body: {
    status?: "publicada" | "erro";
    paginas?: number;
    mensagem?: string;
    pdf_storage_path?: string;
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "JSON inválido" }, { status: 400 });
  }

  const revista = await getRevista(id);
  if (!revista) {
    return NextResponse.json({ error: "Revista não encontrada" }, { status: 404 });
  }

  if (body.status === "publicada") {
    const path = body.pdf_storage_path ?? `${id}.pdf`;
    const paginas = body.paginas ?? 0;
    if (paginas <= 0) {
      return NextResponse.json(
        { error: "Campo 'paginas' obrigatório para status='publicada'" },
        { status: 400 },
      );
    }
    try {
      await markRevistaPublished(id, path, paginas);
    } catch (e) {
      return NextResponse.json(
        { error: e instanceof Error ? e.message : "Erro de DB" },
        { status: 500 },
      );
    }
    return NextResponse.json({ ok: true, status: "publicada" });
  }

  if (body.status === "erro") {
    try {
      await markRevistaErro(id, body.mensagem || "Erro desconhecido na geração");
    } catch (e) {
      return NextResponse.json(
        { error: e instanceof Error ? e.message : "Erro de DB" },
        { status: 500 },
      );
    }
    return NextResponse.json({ ok: true, status: "erro" });
  }

  return NextResponse.json(
    { error: "Status inválido (use 'publicada' ou 'erro')" },
    { status: 400 },
  );
}
