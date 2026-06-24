"use server";

import { readFile } from "node:fs/promises";
import path from "node:path";
import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import {
  CONSVICTA_LIBRARY_FUNDOS,
  CONSVICTA_LIBRARY_ICONS,
  CONSVICTA_LIBRARY_PATTERNS,
} from "./library-manifest";

const BUCKET = "condominios-fotos";

// Mapeamento dos arquivos da biblioteca embutida (public/consvicta-library/)
// pros slots do Supabase. Idempotente: upsert: true, pode ser chamado
// quantas vezes quiser sem duplicar.
const LOGO_MAP: Array<{ slot: number; src: string }> = [
  // slot 1 = wordmark completo (topo de cada slide)
  { slot: 1, src: "public/consvicta-library/logos/wordmark.svg" },
  // slot 2 = símbolo isolado (marca-d'água gigante)
  { slot: 2, src: "public/consvicta-library/logos/symbol.svg" },
];

// Curadoria dos 20 slots de ícones. Slot 2 = capa default, slot 6 = CTA
// default (convenção do engine).
const ICON_MAP: Array<{ slot: number; name: string }> = [
  { slot: 1, name: "Geral_37-edificio" },
  { slot: 2, name: "Geral_05-balancete" },
  { slot: 3, name: "Geral_30-assembleia" },
  { slot: 4, name: "Geral_19-prestacao-contas" },
  { slot: 5, name: "Geral_60-relatorio-financeiro" },
  { slot: 6, name: "Diferenciais_dif-atendimento-24h" },
  { slot: 7, name: "Geral_17-inadimplencia" },
  { slot: 8, name: "Geral_11-equipe" },
  { slot: 9, name: "Geral_57-regulamento" },
  { slot: 10, name: "Geral_08-sindico" },
  { slot: 11, name: "Geral_31-aviso" },
  { slot: 12, name: "Geral_29-comunicado" },
  { slot: 13, name: "Equipe_Multidisciplinar_equipe-juridico" },
  { slot: 14, name: "Diferenciais_dif-reducao-custo" },
  { slot: 15, name: "Geral_24-camera-seguranca" },
  { slot: 16, name: "Geral_25-acesso" },
  { slot: 17, name: "Geral_38-portaria" },
  { slot: 18, name: "Geral_55-agenda" },
  { slot: 19, name: "Geral_58-voto" },
  { slot: 20, name: "Geral_01-documento" },
];

export interface UploadResult {
  ok: boolean;
  uploaded: number;
  failed: number;
  details: Array<{ path: string; ok: boolean; error?: string }>;
}

/** Sobe a biblioteca embutida (logos + 20 icones curados) pros buckets
 *  do Supabase de uma vez. Roda 100% server-side: usa o service_role
 *  já disponível no env Netlify. Idempotente. */
export async function uploadEmbeddedConsvictaAssets(): Promise<UploadResult> {
  // 1. Verifica sessão (mesma proteção das outras pages do dashboard)
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

  // Lê arquivo em modo robusto: tenta vários paths possíveis
  // (process.cwd, __dirname relativo, etc) pra cobrir as variações
  // de bundling do Netlify/Vercel.
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

  const upload = async (localPath: string, remotePath: string) => {
    try {
      const buf = await tryReadFile(localPath);
      const { error } = await sb.storage.from(BUCKET).upload(remotePath, buf, {
        contentType: "image/svg+xml",
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

  // Logos
  for (const { slot, src } of LOGO_MAP) {
    await upload(src, `__consvicta-logos/logo-${slot}.svg`);
  }

  // Icons — todos os 86 da biblioteca embutida. Slots 1-20 sao
  // curados (slot 2 = capa default, slot 6 = CTA default, etc).
  // Slots 21-86 recebem o restante em ordem alfabetica do manifest.
  // Engine usa smart-picker semantico que indexa por keyword no
  // titulo+body, entao a ordem dos slots nao afeta o render — mas
  // tem todos os 86 disponiveis caso queira override manual.
  const iconsRoot = "public/consvicta-library/icons";
  const iconsAll = [...CONSVICTA_LIBRARY_ICONS].sort();
  const curatedSet = new Set(ICON_MAP.map((m) => `${m.name}.svg`));
  const remainingIcons = iconsAll.filter((f) => !curatedSet.has(f));

  // Slots 1-20: curados (mesma ordem do ICON_MAP)
  for (const { slot, name } of ICON_MAP) {
    const file = `${name}.svg`;
    if (!iconsAll.includes(file)) {
      failed += 1;
      details.push({
        path: `__consvicta-icons/icon-${slot}.svg`,
        ok: false,
        error: `arquivo ${file} não está no manifest`,
      });
      continue;
    }
    await upload(
      path.join(iconsRoot, file),
      `__consvicta-icons/icon-${slot}.svg`,
    );
  }
  // Slots 21+: resto da biblioteca em ordem
  for (let i = 0; i < remainingIcons.length; i++) {
    const slot = ICON_MAP.length + 1 + i; // 21, 22, ...
    await upload(
      path.join(iconsRoot, remainingIcons[i]),
      `__consvicta-icons/icon-${slot}.svg`,
    );
  }

  // Patterns — 13 SVGs derivados do brand book (grid dourado, diagonal,
  // simbolo watermark, corner frames, hero textures, dots+frame). O
  // engine carrossel le de __consvicta-patterns/pattern-{slot}.X com
  // pesos por slide (ver _SLIDE_PATTERN_WHITELIST).
  const patternsRoot = "public/consvicta-library/patterns";
  for (let i = 0; i < CONSVICTA_LIBRARY_PATTERNS.length; i++) {
    const slot = i + 1;
    const file = CONSVICTA_LIBRARY_PATTERNS[i];
    await upload(
      path.join(patternsRoot, file),
      `__consvicta-patterns/pattern-${slot}.svg`,
    );
  }

  // Fundos — 20 SVGs decorativos (tiffany glow, grafite linhas, grids,
  // diagonais, gold vertical, circulos concentricos, cantos
  // decorativos, etc). Engine le de __consvicta-icon-carrossel/
  // icon-{slot}.X via _icon_for_slide pra usar como background grande
  // (.icon-bg) de cada slide.
  const fundosRoot = "public/consvicta-library/fundos";
  for (let i = 0; i < CONSVICTA_LIBRARY_FUNDOS.length; i++) {
    const slot = i + 1;
    const file = CONSVICTA_LIBRARY_FUNDOS[i];
    await upload(
      path.join(fundosRoot, file),
      `__consvicta-icon-carrossel/icon-${slot}.svg`,
    );
  }

  revalidatePath("/sindicompany/consvicta-assets");
  return { ok: failed === 0, uploaded, failed, details };
}
