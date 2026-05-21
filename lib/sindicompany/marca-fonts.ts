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
  const display = fams.display.trim();
  const body = fams.body.trim();
  const numeric = fams.numeric.trim() || body;
  if (!display || !body) {
    throw new Error("Informe ao menos a fonte de título e a de corpo.");
  }

  let files: Record<string, Uint8Array>;
  try {
    files = unzipSync(zipBytes);
  } catch {
    throw new Error("Não consegui abrir o .zip — confira se é um zip válido.");
  }

  const uniqueFams = Array.from(new Set([display, body, numeric].filter(Boolean)));
  const supabase = createAdminClient();
  const faces: MarcaFontFace[] = [];
  const skipped: string[] = [];
  let count = 0;

  for (const [path, bytes] of Object.entries(files)) {
    const name = path.split("/").pop() || path;
    // ignora lixo de zip (pasta __MACOSX, dotfiles) e nao-fontes
    if (!name || name.startsWith(".") || path.includes("__MACOSX")) continue;
    if (!FONT_EXT.test(name)) continue;
    if (!bytes.length) continue;
    if (++count > MAX_FILES) {
      throw new Error(`Zip tem fontes demais (máx ${MAX_FILES} arquivos).`);
    }
    const base = name.replace(FONT_EXT, "");
    const fam = matchFamily(base, uniqueFams);
    if (!fam) {
      skipped.push(name);
      continue;
    }
    const dest = `${bucketPrefix}fonts/${name}`;
    const { error } = await supabase.storage
      .from(BUCKET)
      .upload(dest, bytes, { contentType: contentType(name), upsert: true });
    if (error) throw new Error(`Falha ao subir ${name}: ${error.message}`);
    faces.push({
      family: fam,
      weight: parseWeight(base),
      style: parseStyle(base),
      file: name,
    });
  }

  if (faces.length === 0) {
    throw new Error(
      "Nenhum arquivo de fonte casou com os nomes informados. " +
        "Confira se os arquivos do zip começam com o nome da família " +
        "(ex: o arquivo de 'Playfair Display' deve se chamar PlayfairDisplay-Bold.woff2).",
    );
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
