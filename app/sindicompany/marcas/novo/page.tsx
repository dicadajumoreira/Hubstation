import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { DashboardShell } from "../../shell";
import { MarcaForm } from "../marca-form";
import { criarMarcaAction } from "../actions";

export default async function NovaMarcaPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) {
    redirect("/sindicompany/login");
  }
  const params = await searchParams;
  const error = typeof params.error === "string" ? params.error : "";

  return (
    <DashboardShell>
      <main className="max-w-3xl mx-auto px-6 py-12">
        <Link
          href="/sindicompany/marcas"
          className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
        >
          ← Marcas
        </Link>
        <header className="mb-8">
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
            Nova marca
          </div>
          <h1 className="text-3xl font-bold text-onix-900">Cadastrar marca</h1>
          <p className="text-sm text-g60 mt-2 max-w-xl">
            A persona já habilita o copy no tom da marca. A identidade visual
            (logos, paleta, fontes) é populada depois nos Assets da marca.
          </p>
        </header>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 mb-6">
            {error}
          </div>
        )}

        <MarcaForm action={criarMarcaAction} />
      </main>
    </DashboardShell>
  );
}
