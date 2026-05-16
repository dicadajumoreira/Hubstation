"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

const BUCKET = "condominios-fotos";

type UploadIntentFn = (
  slot: number,
  ext: string,
) => Promise<
  | { ok: true; uploadUrl: string; token: string; path: string; publicUrl: string }
  | { ok: false; error: string }
>;

/** Slot genérico de upload de asset (pattern/icon/logo/fundo) — recebe
 *  a server action de upload-intent como prop, então serve tanto pra
 *  os assets BySindicompany quanto pra outros casos futuros. */
export function ByAssetSlot({
  slot,
  label,
  aspect = "square",
  hint,
  initialUrl,
  uploadIntent,
}: {
  slot: number;
  label: string;
  aspect?: "square" | "wide";
  hint?: string;
  initialUrl?: string | null;
  uploadIntent: UploadIntentFn;
}) {
  const [url, setUrl] = useState(initialUrl ?? "");
  const [status, setStatus] = useState<"idle" | "uploading" | "ok" | "error">(
    initialUrl ? "ok" : "idle",
  );
  const [errorMsg, setErrorMsg] = useState("");

  async function handleFile(file: File) {
    setErrorMsg("");
    if (file.size > 10 * 1024 * 1024) {
      setStatus("error");
      setErrorMsg("Arquivo maior que 10MB.");
      return;
    }
    setStatus("uploading");
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    const intent = await uploadIntent(slot, ext);
    if (!intent.ok) {
      setStatus("error");
      setErrorMsg(intent.error);
      return;
    }
    try {
      const supabase = createClient();
      const { error } = await supabase.storage
        .from(BUCKET)
        .uploadToSignedUrl(intent.path, intent.token, file, {
          upsert: true,
          contentType: file.type || undefined,
        });
      if (error) {
        setStatus("error");
        setErrorMsg(error.message || "Falha no upload.");
        return;
      }
      setUrl(`${intent.publicUrl}?v=${Date.now()}`);
      setStatus("ok");
    } catch (e) {
      setStatus("error");
      setErrorMsg(e instanceof Error ? e.message : "Falha desconhecida.");
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-onix-100 bg-white p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-mint-700">
          {label} {slot}
        </span>
        {status === "ok" && <span className="text-[10px] text-g60">Salvo</span>}
      </div>
      {hint && <div className="text-[10px] text-g60 -mt-1">{hint}</div>}
      <div
        className={`${aspect === "wide" ? "aspect-[4/3]" : "aspect-square"} w-full rounded border border-onix-100 bg-onix-50 bg-center bg-no-repeat bg-contain`}
        style={url ? { backgroundImage: `url("${url}")` } : undefined}
      />
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp,image/svg+xml"
        disabled={status === "uploading"}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void handleFile(f);
        }}
        className="block w-full text-xs text-onix-800 file:mr-2 file:rounded file:border file:border-onix-100 file:bg-onix-50 file:px-2 file:py-1 file:text-xs file:font-medium hover:file:bg-onix-100"
      />
      {status === "uploading" && <p className="text-[10px] text-g60">Enviando…</p>}
      {status === "error" && <p className="text-[10px] text-red-700">{errorMsg}</p>}
    </div>
  );
}
