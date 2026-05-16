import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { getRevista, getSignedPdfUrl } from "@/lib/sindicompany/db";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  const { id } = await params;

  let revista;
  try {
    revista = await getRevista(id);
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Erro" },
      { status: 500 },
    );
  }

  if (!revista) {
    return NextResponse.json({ error: "Revista não encontrada" }, { status: 404 });
  }
  if (revista.status !== "publicada" || !revista.pdf_storage_path) {
    return NextResponse.json(
      { error: "Revista ainda não publicada" },
      { status: 409 },
    );
  }

  let signedUrl: string;
  try {
    signedUrl = await getSignedPdfUrl(revista.pdf_storage_path, 3600);
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Erro de storage" },
      { status: 500 },
    );
  }

  // Redireciona pro Supabase Storage com URL assinada (1h).
  return NextResponse.redirect(signedUrl, { status: 302 });
}
