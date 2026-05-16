import { cookies } from "next/headers";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { getRevista, formatEdicao } from "@/lib/sindicompany/db";
import { RevistaProgress } from "./progress";
import {
  cancelarRevistaAction,
  regerarRevistaAction,
  uploadRevistaPdfAction,
} from "./actions";

const STATUS_LABELS = {
  em_producao: "Em produção",
  publicada: "Publicada",
  erro: "Erro",
} as const;

export default async function RevistaPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  const { id } = await params;

  let revista;
  try {
    revista = await getRevista(id);
  } catch (e) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-12">
        <Link href="/sindicompany/dashboard" className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block">
          ← Voltar
        </Link>
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
          <strong>Banco indisponível.</strong> {e instanceof Error ? e.message : String(e)}
        </div>
      </main>
    );
  }

  if (!revista) notFound();

  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <Link
        href="/sindicompany/dashboard"
        className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
      >
        ← Voltar
      </Link>

      <header className="mb-10">
        <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
          {revista.condominio} · {formatEdicao(revista.mes, revista.ano)}
        </div>
        <h1 className="text-3xl font-bold text-onix-900">
          Revista mensal
        </h1>
      </header>

      <section className="rounded-xl border border-onix-100 bg-white p-6 space-y-5">
        {/* Status */}
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-mint-700">
            Status
          </span>
          <span
            className={`inline-block px-2.5 py-0.5 rounded text-xs font-semibold ${
              revista.status === "publicada"
                ? "bg-mint-50 text-mint-700"
                : revista.status === "erro"
                  ? "bg-red-50 text-red-800"
                  : "bg-onix-50 text-onix-800"
            }`}
          >
            {STATUS_LABELS[revista.status]}
          </span>
        </div>

        {/* PDF */}
        {revista.status === "publicada" && revista.pdf_storage_path && (
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-mint-700 mb-1">
              PDF
            </div>
            <a
              href={`/api/sindicompany/revista/${revista.id}/pdf`}
              target="_blank"
              rel="noopener"
              className="text-onix-900 underline font-medium"
            >
              Abrir Revista_{revista.condominio.replace(/\s+/g, "_")}_{String(revista.mes).padStart(2, "0")}_{revista.ano}.pdf
            </a>
            {revista.paginas && (
              <span className="ml-3 text-sm text-g60">
                {revista.paginas} páginas
              </span>
            )}
          </div>
        )}

        {revista.status === "em_producao" && (
          <>
            <RevistaProgress
              createdAt={revista.created_at}
              expectedSeconds={90}
              warnAfterSeconds={180}
            />

            {/* Upload manual como fallback se a engine falhar */}
            <details className="rounded-lg border border-onix-100 bg-white">
              <summary className="px-4 py-2 text-sm font-medium text-onix-900 cursor-pointer hover:bg-onix-50">
                Subir PDF manualmente (fallback)
              </summary>
              <form
                action={uploadRevistaPdfAction}
                encType="multipart/form-data"
                className="px-4 py-3 space-y-3 border-t border-onix-100"
              >
                <input type="hidden" name="id" value={revista.id} />
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-onix-800 mb-1">
                    Arquivo PDF (até 50MB)
                  </label>
                  <input
                    type="file"
                    name="pdf"
                    accept="application/pdf,.pdf"
                    required
                    className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-onix-800 mb-1">
                    Páginas (opcional)
                  </label>
                  <input
                    type="number"
                    name="paginas"
                    min={1}
                    max={200}
                    placeholder="Ex: 32"
                    className="w-32 rounded-lg border border-onix-100 px-3 py-2 text-sm tabular-nums"
                  />
                </div>
                <button
                  type="submit"
                  className="rounded-lg bg-onix-900 text-white px-4 py-2 text-sm font-medium hover:bg-onix-800"
                >
                  Subir PDF e marcar como publicada
                </button>
              </form>
            </details>

            <form action={cancelarRevistaAction}>
              <input type="hidden" name="id" value={revista.id} />
              <button
                type="submit"
                className="text-xs text-red-700 hover:text-red-900 hover:underline"
              >
                Cancelar geração e marcar como erro
              </button>
            </form>
          </>
        )}

        {revista.status === "erro" && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-900">
            <strong>Falha na geração:</strong>{" "}
            {revista.erro_mensagem ?? "sem detalhes"}
            <form action={regerarRevistaAction} className="mt-3">
              <input type="hidden" name="id" value={revista.id} />
              <button
                type="submit"
                className="rounded-lg bg-onix-900 text-white px-4 py-2 text-sm font-medium hover:bg-onix-800"
              >
                Tentar gerar de novo
              </button>
            </form>
          </div>
        )}

        {/* Metadata */}
        <div className="grid grid-cols-2 gap-y-3 gap-x-6 pt-4 border-t border-onix-100 text-sm">
          <div>
            <div className="text-xs uppercase tracking-wider text-mint-700 font-semibold mb-0.5">
              Criada em
            </div>
            <div className="text-onix-800 tabular-nums">
              {new Date(revista.created_at).toLocaleString("pt-BR")}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-mint-700 font-semibold mb-0.5">
              Gerado em
            </div>
            <div className="text-onix-800 tabular-nums">
              {revista.gerado_em
                ? new Date(revista.gerado_em).toLocaleString("pt-BR")
                : "—"}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
