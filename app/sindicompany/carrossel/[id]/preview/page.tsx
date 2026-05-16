import { cookies } from "next/headers";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { getCarrossel } from "@/lib/sindicompany/carrosseis";
import { CarrosselViewer } from "./viewer";

export const dynamic = "force-dynamic";

export default async function CarrosselPreviewPage({
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
  const carrossel = await getCarrossel(id);
  if (!carrossel) notFound();

  const slides = carrossel.png_paths ?? [];
  if (slides.length === 0) {
    return (
      <main className="min-h-screen bg-onix-900 text-white flex flex-col items-center justify-center px-6">
        <p className="text-sm opacity-70 mb-4">Nenhum slide disponível.</p>
        <Link
          href={`/sindicompany/carrossel/${id}`}
          className="text-mint-400 underline underline-offset-2 text-sm"
        >
          ← Voltar
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-onix-900 text-white flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-white/10">
        <div>
          <div className="text-[10px] uppercase tracking-[0.24em] text-mint-400 font-semibold">
            Preview Instagram
          </div>
          <h1 className="text-lg font-medium">{carrossel.titulo}</h1>
        </div>
        <Link
          href={`/sindicompany/carrossel/${id}`}
          className="text-sm text-white/70 hover:text-white"
        >
          ← Fechar
        </Link>
      </header>
      <div className="flex-1 flex items-center justify-center px-6 py-8">
        <CarrosselViewer slides={slides} />
      </div>
    </main>
  );
}
