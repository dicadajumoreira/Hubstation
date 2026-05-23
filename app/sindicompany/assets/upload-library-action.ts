"use server";

import { readFile } from "node:fs/promises";
import path from "node:path";
import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import {
  SINDICOMPANY_LIBRARY_LOGOS,
  SINDICOMPANY_LIBRARY_ICONS,
  SINDICOMPANY_LIBRARY_PATTERNS,
} from "./library-manifest";

const BUCKET = "condominios-fotos";
const LIB = "public/sindicompany-library";

// Mapeamento dos arquivos da biblioteca embutida (public/sindicompany-library/)
// pros slots do Supabase no bucket Sindicompany (__logos, __icons, __patterns).
// Idempotente: upsert: true, pode ser chamado quantas vezes quiser sem
// duplicar. Alimenta a GALERIA de assets (/sindicompany/assets); o engine
// usa as fontes/masks/patterns embutidos no proprio repo, nao o bucket.
const LOGO_MAP: Array<{ slot: number; src: string; ext: string }> = [
  { slot: 1, src: `${LIB}/logos/sindicompany-horizontal-color.png`, ext: "png" },
  { slot: 2, src: `${LIB}/logos/sindicompany-horizontal-white.png`, ext: "png" },
  { slot: 3, src: `${LIB}/logos/sindicompany-horizontal-cyan.png`, ext: "png" },
  { slot: 4, src: `${LIB}/logos/sindicompany-horizontal-lavender.png`, ext: "png" },
  { slot: 5, src: `${LIB}/logos/sindicompany-horizontal-dark.png`, ext: "png" },
  { slot: 6, src: `${LIB}/logos/mask-houses.png`, ext: "png" },
  { slot: 7, src: `${LIB}/logos/mask-dot.png`, ext: "png" },
  { slot: 8, src: `${LIB}/logos/mask-outer-filled.png`, ext: "png" },
  { slot: 9, src: `${LIB}/logos/sindicompany-horizontal-color-2.png`, ext: "png" },
  { slot: 10, src: `${LIB}/logos/sindicompany-horizontal-color-alt.png`, ext: "png" },
];

const ICON_MAP: Array<{ slot: number; src: string; ext: string }> = [
  { slot: 1, src: `${LIB}/icons/icon-cyan-beige.png`, ext: "png" },
  { slot: 2, src: `${LIB}/icons/icon-beige-lavender.png`, ext: "png" },
  { slot: 3, src: `${LIB}/icons/icon-dark.png`, ext: "png" },
  { slot: 4, src: `${LIB}/icons/icon-white.png`, ext: "png" },
  { slot: 5, src: `${LIB}/icons/icon-cyan-photo.png`, ext: "png" },
  { slot: 6, src: `${LIB}/icons/icon-beige-photo.png`, ext: "png" },
];

const PATTERN_MAP: Array<{ slot: number; src: string; ext: string }> = [
  { slot: 1, src: `${LIB}/patterns/canto-navy.png`, ext: "png" },
  { slot: 2, src: `${LIB}/patterns/canto-cyan.png`, ext: "png" },
  { slot: 3, src: `${LIB}/patterns/canto-beige.png`, ext: "png" },
  { slot: 4, src: `${LIB}/patterns/canto-lavender.png`, ext: "png" },
  { slot: 5, src: `${LIB}/patterns/canto-purple.png`, ext: "png" },
  { slot: 6, src: `${LIB}/patterns/criativo-direito-navy.png`, ext: "png" },
  { slot: 7, src: `${LIB}/patterns/criativo-direito-beige.png`, ext: "png" },
  { slot: 8, src: `${LIB}/patterns/criativo-direito-purple.png`, ext: "png" },
  { slot: 9, src: `${LIB}/patterns/criativo-esquerdo-navy.png`, ext: "png" },
  { slot: 10, src: `${LIB}/patterns/decorativo-navy-2.png`, ext: "png" },
  { slot: 11, src: `${LIB}/patterns/decorativo-beige-2.png`, ext: "png" },
  { slot: 12, src: `${LIB}/patterns/decorativo-purple-2.png`, ext: "png" },
  { slot: 13, src: `${LIB}/patterns/fundo-circ-navy.png`, ext: "png" },
  { slot: 14, src: `${LIB}/patterns/fundo-circ-cyan.png`, ext: "png" },
  { slot: 15, src: `${LIB}/patterns/fundo-circ-beige.png`, ext: "png" },
  { slot: 16, src: `${LIB}/patterns/fundo-geo-navy.png`, ext: "png" },
  { slot: 17, src: `${LIB}/patterns/fundo-geo-beige.png`, ext: "png" },
];

export interface UploadResult {
  ok: boolean;
  uploaded: number;
  failed: number;
  details: Array<{ path: string; ok: boolean; error?: string }>;
}

/** Sobe a biblioteca embutida (logos + masks) pros buckets do Supabase
 *  Sindicompany de uma vez. Roda 100% server-side: usa o service_role
 *  já disponível no env Netlify. Idempotente.
 *
 *  Hoje só sobe logos+masks (os 4 PNGs embutidos do Brand Hub novo).
 *  Patterns e icons coloridos do ZIP "Sindicompany Assets" podem ser
 *  uploadados manualmente via UI de slots ou expandindo o manifest
 *  + LOGO_MAP/PATTERN_MAP/ICON_MAP acima quando os PNGs estiverem
 *  extraídos em `public/sindicompany-library/`. */
export async function uploadEmbeddedSindicompanyAssets(): Promise<UploadResult> {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    return {
      ok: false,
      uploaded: 0,
      failed: 0,
      details: [{ path: "auth", ok: false, error: "Sessão inválida" }],
    };
  }

  const sb = createAdminClient();
  const details: UploadResult["details"] = [];
  let uploaded = 0;
  let failed = 0;

  const tryReadFile = async (relPath: string): Promise<Buffer> => {
    const candidates = [
      relPath,
      path.join(process.cwd(), relPath),
      path.join(process.cwd(), ".next", "standalone", relPath),
      path.join(process.cwd(), ".next", "server", relPath),
    ];
    let lastErr: Error | null = null;
    for (const p of candidates) {
      try {
        return await readFile(p);
      } catch (e) {
        lastErr = e as Error;
      }
    }
    throw lastErr ?? new Error(`Não encontrei ${relPath} em nenhum candidato`);
  };

  const upload = async (localPath: string, remotePath: string, contentType: string) => {
    try {
      const buf = await tryReadFile(localPath);
      const { error } = await sb.storage.from(BUCKET).upload(remotePath, buf, {
        contentType,
        upsert: true,
      });
      if (error) throw new Error(error.message);
      uploaded += 1;
      details.push({ path: remotePath, ok: true });
    } catch (e) {
      failed += 1;
      const msg = e instanceof Error ? e.message : String(e);
      details.push({ path: remotePath, ok: false, error: msg });
    }
  };

  // Logos + masks (__logos/logo-N), icones (__icons/icon-N) e patterns
  // (__patterns/pattern-N). svg+png — content-type derivado da ext.
  const ctype = (ext: string) =>
    ext === "svg" ? "image/svg+xml" : `image/${ext}`;
  for (const { slot, src, ext } of LOGO_MAP) {
    await upload(src, `__logos/logo-${slot}.${ext}`, ctype(ext));
  }
  for (const { slot, src, ext } of ICON_MAP) {
    await upload(src, `__icons/icon-${slot}.${ext}`, ctype(ext));
  }
  for (const { slot, src, ext } of PATTERN_MAP) {
    await upload(src, `__patterns/pattern-${slot}.${ext}`, ctype(ext));
  }

  // Sanity check: confirma que cada arquivo do manifest esta mapeado.
  const checks: Array<[readonly string[], typeof LOGO_MAP, string]> = [
    [SINDICOMPANY_LIBRARY_LOGOS, LOGO_MAP, "LOGO_MAP"],
    [SINDICOMPANY_LIBRARY_ICONS, ICON_MAP, "ICON_MAP"],
    [SINDICOMPANY_LIBRARY_PATTERNS, PATTERN_MAP, "PATTERN_MAP"],
  ];
  for (const [manifest, map, name] of checks) {
    for (const file of manifest) {
      if (!map.some((m) => m.src.endsWith(file))) {
        details.push({
          path: `manifest:${file}`,
          ok: false,
          error: `arquivo no manifest mas nao mapeado — verifica ${name}`,
        });
        failed += 1;
      }
    }
  }

  revalidatePath("/sindicompany/assets");
  return { ok: failed === 0, uploaded, failed, details };
}
