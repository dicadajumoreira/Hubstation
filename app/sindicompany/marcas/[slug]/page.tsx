import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { getMarca } from "@/lib/sindicompany/marcas-db";
import { DashboardShell } from "../../shell";
import { MarcaForm } from "../marca-form";
import { atualizarMarcaAction } from "../actions";

export default async function EditarMarcaPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) {
    redirect("/sindicompany/login");
  }
  const { slug } = await params;
  const sp = await searchParams;
  const error = typeof sp.error === "string" ? sp.error : "";

  const marca = await getMarca(slug);
  if (!marca) notFound();

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
            Editar marca
          </div>
          <h1 className="text-3xl font-bold text-onix-900">{marca.nome}</h1>
          <p className="text-sm text-g60 mt-2">{marca.handle}</p>
        </header>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 mb-6">
            {error}
          </div>
        )}

        <MarcaForm action={atualizarMarcaAction} marca={marca} />
      </main>
    </DashboardShell>
  );
}
