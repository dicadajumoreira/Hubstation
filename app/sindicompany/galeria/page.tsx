import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { DashboardShell } from "../shell";
import { GalleryGrid, type GalleryItem } from "./gallery-grid";

const BUCKET = "condominios-fotos";
const IMG = /\.(png|jpe?g|webp|svg)$/i;

// Categorias varridas (bucket prefix sindicompany __ + leaf). Mostra tudo
// que foi subido, sem precisar navegar a hierarquia.
const CATEGORIES: Array<{ label: string; prefix: string }> = [
  { label: "Logotipos", prefix: "__logos" },
  { label: "Ícones", prefix: "__icons" },
  { label: "Patterns", prefix: "__patterns" },
  { label: "Fundos", prefix: "__fundos" },
];

export const dynamic = "force-dynamic";

export default async function GaleriaPage() {
  const store = await cookies();
  if (!verifySessionToken(store.get(SESSION_COOKIE)?.value)) {
    redirect("/sindicompany/login");
  }

  const items: GalleryItem[] = [];
  try {
    const sb = createAdminClient();
    for (const cat of CATEGORIES) {
      const { data } = await sb.storage
        .from(BUCKET)
        .list(cat.prefix, { limit: 1000, sortBy: { column: "name", order: "asc" } });
      for (const obj of data ?? []) {
        if (!IMG.test(obj.name)) continue;
        const { data: pub } = sb.storage
          .from(BUCKET)
          .getPublicUrl(`${cat.prefix}/${obj.name}`);
        const v = obj.updated_at ?? obj.created_at ?? "";
        items.push({
          url: `${pub.publicUrl}?v=${v}`,
          name: obj.name,
          category: cat.label,
        });
      }
    }
  } catch {
    // sem credencial/listagem — grid vazio
  }

  return (
    <DashboardShell>
      <main className="max-w-5xl mx-auto px-6 py-12 space-y-8">
        <Link
          href="/sindicompany/assets"
          className="text-sm text-g60 hover:text-onix-900 inline-block"
        >
          ← Assets
        </Link>
        <header>
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2">
            Galeria · @sindicompanybr
          </div>
          <h1 className="text-3xl font-bold text-onix-900 mb-2">
            Galeria de assets
          </h1>
          <p className="text-sm text-g60 max-w-2xl">
            Todos os arquivos da marca num só lugar — logos, ícones, patterns e
            fundos. {items.length} arquivo{items.length === 1 ? "" : "s"} no
            total. Use os painéis de categoria pra subir novos (ou o ZIP).
          </p>
        </header>

        <GalleryGrid items={items} />
      </main>
    </DashboardShell>
  );
}
