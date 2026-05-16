#!/usr/bin/env node
/**
 * upload-consvicta-assets.mjs
 *
 * Sobe todos os assets da Consvicta (logos + icons) pros buckets do Supabase
 * usados pela página /sindicompany/consvicta-assets e pelo engine de
 * carrossel.
 *
 * Lê os SVGs de public/consvicta-library/ (que estão no repo) e escreve em:
 *   condominios-fotos/__consvicta-logos/logo-{1,2}.svg
 *   condominios-fotos/__consvicta-icons/icon-{1..20}.svg
 *
 * Idempotente: usa upsert, pode rodar quantas vezes quiser.
 *
 * USO:
 *   1. Garanta que .env.local tem NEXT_PUBLIC_SUPABASE_URL +
 *      SUPABASE_SERVICE_ROLE_KEY com os valores REAIS de produção.
 *   2. node scripts/upload-consvicta-assets.mjs
 *   3. (Opcional) node scripts/upload-consvicta-assets.mjs --dry-run
 *      pra ver o que SERIA enviado sem subir nada.
 */

import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { createClient } from "@supabase/supabase-js";

// ─────────────────────────────────────────────────────────────────────────────
// Env
// ─────────────────────────────────────────────────────────────────────────────

async function loadEnvLocal() {
  try {
    const txt = await readFile(".env.local", "utf-8");
    for (const line of txt.split("\n")) {
      const m = line.match(/^\s*([A-Z_]+)\s*=\s*(.+?)\s*$/);
      if (!m) continue;
      const [, k, v] = m;
      if (!process.env[k]) {
        process.env[k] = v.replace(/^["']|["']$/g, "");
      }
    }
  } catch {
    // sem .env.local — assume que env já está exportado
  }
}

await loadEnvLocal();

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const DRY_RUN = process.argv.includes("--dry-run");

if (!SUPABASE_URL || !SERVICE_KEY) {
  console.error(
    "✗ Faltam env vars. Defina NEXT_PUBLIC_SUPABASE_URL e " +
      "SUPABASE_SERVICE_ROLE_KEY (no .env.local ou exportado).",
  );
  process.exit(1);
}
if (SUPABASE_URL.includes("example.supabase.co")) {
  console.error(
    "✗ NEXT_PUBLIC_SUPABASE_URL ainda é o placeholder 'example.supabase.co'. " +
      "Use a URL real do Supabase de produção.",
  );
  process.exit(1);
}

const sb = createClient(SUPABASE_URL, SERVICE_KEY, {
  auth: { persistSession: false },
});
const BUCKET = "condominios-fotos";

// ─────────────────────────────────────────────────────────────────────────────
// Mapeamento: o que sobe em qual slot
// ─────────────────────────────────────────────────────────────────────────────

// Logos (2 arquivos)
const LOGO_MAP = [
  // slot 1 = wordmark (CONSVICTA + símbolo) → aparece no TOPO de cada slide
  { slot: 1, src: "public/consvicta-library/logos/wordmark.svg" },
  // slot 2 = símbolo isolado → vira marca-d'água gigante atrás dos slides
  { slot: 2, src: "public/consvicta-library/logos/symbol.svg" },
];

// Icons (20 slots). Curadoria escolhida com base no que mais aparece em
// carrosséis de gestão condominial. Ordem importante: slot 2 = capa,
// slot 6 = CTA (convenção legacy do engine).
const ICON_MAP = [
  { slot: 1, name: "Geral_37-edificio" }, // prédio
  { slot: 2, name: "Geral_05-balancete" }, // capa default
  { slot: 3, name: "Geral_30-assembleia" }, // assembleia
  { slot: 4, name: "Geral_19-prestacao-contas" }, // prestação
  { slot: 5, name: "Geral_60-relatorio-financeiro" }, // financeiro
  { slot: 6, name: "Diferenciais_dif-atendimento-24h" }, // CTA default
  { slot: 7, name: "Geral_17-inadimplencia" }, // alerta
  { slot: 8, name: "Geral_11-equipe" }, // equipe
  { slot: 9, name: "Geral_57-regulamento" }, // regulamento
  { slot: 10, name: "Geral_08-sindico" }, // síndico
  { slot: 11, name: "Geral_31-aviso" }, // aviso
  { slot: 12, name: "Geral_29-comunicado" }, // comunicado
  { slot: 13, name: "Equipe_Multidisciplinar_equipe-juridico" }, // jurídico
  { slot: 14, name: "Diferenciais_dif-reducao-custo" }, // economia
  { slot: 15, name: "Geral_24-camera-seguranca" }, // segurança
  { slot: 16, name: "Geral_25-acesso" }, // acesso
  { slot: 17, name: "Geral_38-portaria" }, // portaria
  { slot: 18, name: "Geral_55-agenda" }, // agenda
  { slot: 19, name: "Geral_58-voto" }, // voto
  { slot: 20, name: "Geral_01-documento" }, // documento
];

// ─────────────────────────────────────────────────────────────────────────────
// Upload
// ─────────────────────────────────────────────────────────────────────────────

async function upload(localPath, remotePath) {
  const buf = await readFile(localPath);
  if (DRY_RUN) {
    console.log(`  [dry-run] ${localPath}  →  ${BUCKET}/${remotePath}  (${buf.length}B)`);
    return;
  }
  const { error } = await sb.storage.from(BUCKET).upload(remotePath, buf, {
    contentType: "image/svg+xml",
    upsert: true,
  });
  if (error) {
    throw new Error(`upload ${remotePath}: ${error.message}`);
  }
  console.log(`  ✓ ${remotePath}`);
}

async function main() {
  console.log(
    `${DRY_RUN ? "[DRY-RUN] " : ""}Subindo assets Consvicta em ` +
      `${SUPABASE_URL.replace(/^https?:\/\//, "")}/${BUCKET}\n`,
  );

  // Verifica que os arquivos fonte existem
  const iconsRoot = "public/consvicta-library/icons";
  const iconFiles = new Set(
    (await readdir(iconsRoot).catch(() => [])).filter((f) =>
      f.endsWith(".svg"),
    ),
  );

  // — Logos
  console.log("Logotipos:");
  for (const { slot, src } of LOGO_MAP) {
    try {
      await upload(src, `__consvicta-logos/logo-${slot}.svg`);
    } catch (e) {
      console.error(`  ✗ slot ${slot}: ${e.message}`);
    }
  }

  // — Icons
  console.log("\nÍcones (20 slots curados):");
  for (const { slot, name } of ICON_MAP) {
    const file = `${name}.svg`;
    if (!iconFiles.has(file)) {
      console.error(`  ✗ slot ${slot}: arquivo ${file} não encontrado em ${iconsRoot}`);
      continue;
    }
    try {
      await upload(join(iconsRoot, file), `__consvicta-icons/icon-${slot}.svg`);
    } catch (e) {
      console.error(`  ✗ slot ${slot}: ${e.message}`);
    }
  }

  console.log(
    `\n${DRY_RUN ? "[DRY-RUN] nada foi enviado." : "Concluído."} ` +
      `Confira em /sindicompany/consvicta-assets.`,
  );
}

main().catch((e) => {
  console.error("✗ Falha geral:", e.message);
  process.exit(1);
});
