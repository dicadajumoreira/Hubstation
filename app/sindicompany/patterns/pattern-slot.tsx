"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { getPatternUploadIntent } from "../revista/nova/upload-actions";

const BUCKET = "condominios-fotos";

interface PatternSlotProps {
  slot: number;
  initialUrl?: string | null;
}

export function PatternSlot({ slot, initialUrl }: PatternSlotProps) {
  const [url, setUrl] = useState(initialUrl ?? "");
  const [status, setStatus] = useState<"idle" | "uploading" | "ok" | "error">(
    initialUrl ? "ok" : "idle",
  );
  const [errorMsg, setErrorMsg] = useState("");

  async function handleFile(file: File) {
    setErrorMsg("");
    if (file.size > 20 * 1024 * 1024) {
      setStatus("error");
      setErrorMsg("Imagem maior que 20MB.");
      return;
    }
    setStatus("uploading");
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    const intent = await getPatternUploadIntent(slot, ext);
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
      // Cache-bust appending timestamp
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
          Pattern {slot}
        </span>
        {status === "ok" && (
          <span className="text-[10px] text-g60">Salvo</span>
        )}
      </div>
      <div
        className="aspect-square w-full rounded border border-onix-100 bg-onix-50 bg-center bg-no-repeat bg-contain"
        style={url ? { backgroundImage: `url("${url}")` } : undefined}
      />
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        disabled={status === "uploading"}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void handleFile(f);
        }}
        className="block w-full text-xs text-onix-800 file:mr-2 file:rounded file:border file:border-onix-100 file:bg-onix-50 file:px-2 file:py-1 file:text-xs file:font-medium hover:file:bg-onix-100"
      />
      {status === "uploading" && (
        <p className="text-[10px] text-g60">Enviando…</p>
      )}
      {status === "error" && (
        <p className="text-[10px] text-red-700">{errorMsg}</p>
      )}
    </div>
  );
}
