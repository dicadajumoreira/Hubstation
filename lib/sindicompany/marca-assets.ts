import { createAdminClient } from "@/lib/supabase/admin";

// Logos/ícones da marca ficam no mesmo bucket dos demais assets, nos slots
// que o engine procura: {prefix}logos/logo-{n}.{ext} e
// {prefix}icons/icon-{n}.{ext}. O engine tenta as extensões nesta ordem.
const BUCKET = "condominios-fotos";
const IMG_EXT = ["png", "svg", "webp", "jpg", "jpeg"] as const;
const ALLOWED = new Set(IMG_EXT);

export interface MarcaAssetSlot {
  /** Nome do campo no formulário. */
  field: string;
  kind: "logos" | "icons";
  slot: number;
  label: string;
  hint: string;
}

// Slots expostos no cadastro — batem com o que o engine usa para marca nova
// (vide carrossel_generate.py: logo_top_slot=5; símbolo = logo 2/3/1;
// ícone de capa = icon 2; ícone de CTA = icon 6).
export const MARCA_ASSET_SLOTS: MarcaAssetSlot[] = [
  {
    field: "logo_principal",
    kind: "logos",
    slot: 5,
    label: "Logo principal",
    hint: "Aparece no topo de todos os slides.",
  },
  {
    field: "logo_simbolo",
    kind: "logos",
    slot: 2,
    label: "Símbolo da marca",
    hint: "Marca/ícone usado em capas e no CTA.",
  },
  {
    field: "icone_capa",
    kind: "icons",
    slot: 2,
    label: "Ícone de capa",
    hint: "Ícone exibido na capa do carrossel.",
  },
  {
    field: "icone_cta",
    kind: "icons",
    slot: 6,
    label: "Ícone de CTA",
    hint: "Ícone do slide final (chamada para ação).",
  },
];

function normExt(name: string): string | null {
  const m = name.toLowerCase().match(/\.([a-z0-9]+)$/);
  if (!m) return null;
  const ext = m[1] === "jpeg" ? "jpg" : m[1];
  return ALLOWED.has(ext as (typeof IMG_EXT)[number]) ? ext : null;
}

function contentType(ext: string, fileType: string): string {
  if (fileType) return fileType;
  if (ext === "svg") return "image/svg+xml";
  if (ext === "jpg") return "image/jpeg";
  return `image/${ext}`;
}

/** Sobe os logos/ícones presentes no formulário pros slots da marca.
 *  Campo vazio = mantém o asset atual. Devolve quantos arquivos subiu.
 *  Lança Error amigável em formato inválido / falha de upload. */
export async function uploadMarcaAssets(
  fd: FormData,
  bucketPrefix: string,
): Promise<number> {
  const supabase = createAdminClient();
  let count = 0;
  for (const a of MARCA_ASSET_SLOTS) {
    const file = fd.get(a.field);
    if (!(file instanceof File) || file.size === 0) continue;
    const ext = normExt(file.name);
    if (!ext) {
      throw new Error(`${a.label}: formato inválido — use PNG, SVG, WEBP ou JPG.`);
    }
    const bytes = new Uint8Array(await file.arrayBuffer());
    const stem = a.kind === "logos" ? "logo" : "icon";
    const basePath = `${bucketPrefix}${a.kind}/${stem}-${a.slot}`;
    // Remove variantes de outras extensões pra nenhuma sombrear a nova na
    // busca do engine (que tenta png, svg, webp, jpg, jpeg nessa ordem).
    await supabase.storage
      .from(BUCKET)
      .remove(IMG_EXT.map((e) => `${basePath}.${e}`))
      .catch(() => {});
    const { error } = await supabase.storage
      .from(BUCKET)
      .upload(`${basePath}.${ext}`, bytes, {
        contentType: contentType(ext, file.type),
        upsert: true,
      });
    if (error) throw new Error(`Falha ao subir ${a.label}: ${error.message}`);
    count++;
  }
  return count;
}
