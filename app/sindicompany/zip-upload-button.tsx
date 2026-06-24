"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { unzipSync } from "fflate";
import { createClient } from "@/lib/supabase/client";

const BUCKET = "condominios-fotos";
const IMG_EXT = new Set(["png", "jpg", "jpeg", "webp", "svg"]);

type UploadIntentFn = (
  slot: number,
  ext: string,
) => Promise<
  | { ok: true; uploadUrl: string; token: string; path: string; publicUrl: string }
  | { ok: false; error: string }
>;

/** Carrega UM .zip e distribui os arquivos de imagem (png/jpg/webp/svg)
 *  nos slots desta categoria, a partir de `startSlot` (anexa sem
 *  sobrescrever os existentes). Extrai no browser (fflate) e sobe cada
 *  arquivo via signed URL — sem limite de body de server action. */
export function ZipUploadButton({
  startSlot,
  uploadIntent,
}: {
  startSlot: number;
  uploadIntent: UploadIntentFn;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [result, setResult] = useState<{ ok: number; fail: number } | null>(null);

  async function handleZip(file: File) {
    setResult(null);
    setMsg("Lendo ZIP…");
    setBusy(true);
    try {
      const buf = new Uint8Array(await file.arrayBuffer());
      const files = unzipSync(buf);
      const entries = Object.entries(files).filter(([name, bytes]) => {
        if (name.endsWith("/")) return false;
        if (name.includes("__MACOSX")) return false;
        const base = name.split("/").pop() ?? "";
        if (!base || base.startsWith(".")) return false;
        const ext = base.split(".").pop()?.toLowerCase() ?? "";
        return IMG_EXT.has(ext) && bytes.length > 0;
      });
      if (entries.length === 0) {
        setMsg("Nenhuma imagem (png/jpg/webp/svg) encontrada no ZIP.");
        setBusy(false);
        return;
      }
      const supabase = createClient();
      let ok = 0;
      let fail = 0;
      for (let i = 0; i < entries.length; i++) {
        const [name, bytes] = entries[i];
        const ext = (name.split(".").pop() ?? "").toLowerCase();
        const slot = startSlot + i;
        setMsg(`Enviando ${i + 1}/${entries.length}…`);
        const intent = await uploadIntent(slot, ext);
        if (!intent.ok) {
          fail += 1;
          continue;
        }
        const ct = ext === "svg" ? "image/svg+xml" : `image/${ext}`;
        // Uint8Array -> BlobPart. Copia pro buffer exato do arquivo.
        const blob = new Blob([bytes.slice()], { type: ct });
        const { error } = await supabase.storage
          .from(BUCKET)
          .uploadToSignedUrl(intent.path, intent.token, blob, {
            upsert: true,
            contentType: ct,
          });
        if (error) fail += 1;
        else ok += 1;
      }
      setResult({ ok, fail });
      setMsg("");
      router.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Falha ao ler o ZIP.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-onix-200 bg-white p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-onix-900 mb-1">
            Carregar ZIP
          </h3>
          <p className="text-xs text-g60 sm:max-w-xl">
            Sobe um único .zip e distribui as imagens (PNG/JPG/WebP/SVG) nos
            slots desta categoria, a partir do slot {startSlot}. Não
            sobrescreve os já preenchidos.
          </p>
        </div>
        <label
          className={`block sm:w-auto shrink-0 cursor-pointer rounded-md text-center text-sm font-semibold px-4 py-3 sm:py-2 transition ${
            busy
              ? "bg-onix-200 text-onix-500 cursor-wait"
              : "bg-mint-600 text-white hover:bg-mint-700"
          }`}
        >
          {busy ? "Enviando…" : "Escolher ZIP"}
          <input
            type="file"
            accept=".zip,application/zip,application/x-zip-compressed"
            disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void handleZip(f);
              e.target.value = "";
            }}
            className="hidden"
          />
        </label>
      </div>

      {(msg || result) && (
        <div className="mt-3 rounded-md bg-onix-50 border border-onix-100 px-3 py-2 text-xs">
          {msg && <span className="text-onix-800">{msg}</span>}
          {result && (
            <span
              className={result.fail > 0 ? "text-rose-700" : "text-mint-800 font-medium"}
            >
              ✓ {result.ok} enviado{result.ok === 1 ? "" : "s"}
              {result.fail > 0 ? `, ${result.fail} falhou` : ", 0 falhas"}.
            </span>
          )}
        </div>
      )}
    </div>
  );
}
