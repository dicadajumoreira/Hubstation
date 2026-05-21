import { unzipSync } from "fflate";
import { createAdminClient } from "@/lib/supabase/admin";
import type { MarcaFontFace, MarcaTipografia } from "./marcas-db";

// Fontes da marca ficam no MESMO bucket dos outros assets (logos/icons),
// sob {bucketPrefix}fonts/. O engine le de la e embute em base64.
const BUCKET = "condominios-fotos";
const FONT_EXT = /\.(woff2|woff|otf|ttf)$/i;
const MAX_FILES = 60;

function norm(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, "");
}

// Acha qual familia digitada (display/body/numeric) o arquivo pertence,
// comparando o nome normalizado. Pega o match mais especifico (prefixo
// mais longo) pra "Inter" nao roubar arquivo de "Inter Tight".
function matchFamily(base: string, fams: string[]): string | null {
  const nb = norm(base);
  let best: string | null = null;
  let bestLen = 0;
  for (const f of fams) {
    const nf = norm(f);
    if (nf && nb.startsWith(nf) && nf.length > bestLen) {
      best = f;
      bestLen = nf.length;
    }
  }
  return best;
}

// Deriva o peso do nome do arquivo. Fonte variavel (cobre todos os pesos
// num arquivo so) -> range "100 900". Numero explicito vence; senao casa
// tokens nomeados (especifico antes do generico). Default 400.
function parseWeight(base: string): number | string {
  if (/variablefont|wght/i.test(base)) return "100 900";
  const num = base.match(/(?:^|[^0-9])([1-9]00)(?:[^0-9]|$)/);
  if (num) return parseInt(num[1], 10);
  const b = base.toLowerCase();
  if (/thin|hairline/.test(b)) return 100;
  if (/extra-?light|ultra-?light/.test(b)) return 200;
  if (/semi-?bold|demi-?bold/.test(b)) return 600;
  if (/extra-?bold|ultra-?bold/.test(b)) return 800;
  if (/black|heavy/.test(b)) return 900;
  if (/bold/.test(b)) return 700;
  if (/medium/.test(b)) return 500;
  if (/light/.test(b)) return 300;
  return 400;
}

function parseStyle(base: string): "normal" | "italic" {
  return /italic|oblique/i.test(base) ? "italic" : "normal";
}

function contentType(name: string): string {
  const ext = (name.match(FONT_EXT)?.[1] || "").toLowerCase();
  if (ext === "woff2") return "font/woff2";
  if (ext === "woff") return "font/woff";
  if (ext === "otf") return "font/otf";
  return "font/ttf";
}

export interface ProcessFontZipResult {
  tipografia: MarcaTipografia;
  registered: number;
  skipped: string[];
}

/** Descompacta o ZIP, sobe cada arquivo de fonte pro bucket em
 *  {bucketPrefix}fonts/ e monta a tipografia (faces + stacks CSS).
 *  Lanca Error com mensagem amigavel em caso de problema. */
export async function processFontZip(
  zipBytes: Uint8Array,
  bucketPrefix: string,
  fams: { display: string; body: string; numeric: string },
): Promise<ProcessFontZipResult> {
  return processFontZips([zipBytes], bucketPrefix, fams);
}

// Preferencia de formato no de-dup: woff2 (menor) > woff > otf > ttf.
function formatRank(name: string): number {
  const e = name.toLowerCase();
  if (e.endsWith(".woff2")) return 4;
  if (e.endsWith(".woff")) return 3;
  if (e.endsWith(".otf")) return 2;
  return 1;
}

/** Processa um ou mais ZIPs de fontes. De-duplica por familia+peso+estilo
 *  preferindo o formato mais leve (woff2), sobe os vencedores pro bucket e
 *  monta a tipografia. Lanca Error amigavel em problema. */
export async function processFontZips(
  zips: Uint8Array[],
  bucketPrefix: string,
  fams: { display: string; body: string; numeric: string },
): Promise<ProcessFontZipResult> {
  const display = fams.display.trim();
  const body = fams.body.trim();
  const numeric = fams.numeric.trim() || body;
  if (!display || !body) {
    throw new Error("Informe ao menos a fonte de título e a de corpo.");
  }
  const uniqueFams = Array.from(new Set([display, body, numeric].filter(Boolean)));

  // Fase 1: junta candidatos de todos os zips (sem subir ainda).
  interface Cand {
    name: string;
    bytes: Uint8Array;
    family: string;
    weight: number | string;
    style: "normal" | "italic";
  }
  const best = new Map<string, Cand>();
  const skipped: string[] = [];

  for (const zipBytes of zips) {
    let files: Record<string, Uint8Array>;
    try {
      files = unzipSync(zipBytes);
    } catch {
      throw new Error("Não consegui abrir um dos .zip — confira se é um zip válido.");
    }
    for (const [path, bytes] of Object.entries(files)) {
      const name = path.split("/").pop() || path;
      if (!name || name.startsWith(".") || path.includes("__MACOSX")) continue;
      if (!FONT_EXT.test(name)) continue;
      if (!bytes.length) continue;
      const base = name.replace(FONT_EXT, "");
      const family = matchFamily(base, uniqueFams);
      if (!family) {
        skipped.push(name);
        continue;
      }
      const weight = parseWeight(base);
      const style = parseStyle(base);
      const key = `${family}|${weight}|${style}`;
      const cur = best.get(key);
      // Mantem o formato mais leve quando o mesmo peso aparece duplicado
      // (ex: pacote com .ttf E .woff2 do mesmo Bold).
      if (!cur || formatRank(name) > formatRank(cur.name)) {
        best.set(key, { name, bytes, family, weight, style });
      }
    }
  }

  const cands = Array.from(best.values());
  if (cands.length === 0) {
    throw new Error(
      "Nenhum arquivo de fonte casou com os nomes informados. " +
        "Confira se os arquivos do zip começam com o nome da família " +
        "(ex: o arquivo de 'Playfair Display' deve se chamar PlayfairDisplay-Bold.woff2).",
    );
  }
  if (cands.length > MAX_FILES) {
    throw new Error(`Fontes demais (${cands.length}); máximo ${MAX_FILES}.`);
  }

  // Fase 2: sobe os vencedores.
  const supabase = createAdminClient();
  const faces: MarcaFontFace[] = [];
  for (const c of cands) {
    const dest = `${bucketPrefix}fonts/${c.name}`;
    const { error } = await supabase.storage
      .from(BUCKET)
      .upload(dest, c.bytes, { contentType: contentType(c.name), upsert: true });
    if (error) throw new Error(`Falha ao subir ${c.name}: ${error.message}`);
    faces.push({ family: c.family, weight: c.weight, style: c.style, file: c.name });
  }

  return {
    tipografia: {
      display: `'${display}', Georgia, serif`,
      body: `'${body}', system-ui, sans-serif`,
      numeric: `'${numeric}', system-ui, sans-serif`,
      faces,
    },
    registered: faces.length,
    skipped,
  };
}

