"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import {
  getCarrosselFotoUploadIntent,
  salvarSlideFotoAction,
} from "./actions";

const BUCKET = "condominios-fotos";

export function SlideFotoUpload({
  carrosselId,
  slideIdx,
  initialUrl,
}: {
  carrosselId: string;
  slideIdx: number;
  initialUrl?: string | null;
}) {
  const [url, setUrl] = useState(initialUrl ?? "");
  const [status, setStatus] = useState<"idle" | "uploading" | "ok" | "error">(
    initialUrl ? "ok" : "idle",
  );
  const [errorMsg, setErrorMsg] = useState("");

  async function handleFile(file: File) {
    setErrorMsg("");
    if (file.size > 30 * 1024 * 1024) {
      setStatus("error");
      setErrorMsg("Foto maior que 30MB.");
      return;
    }
    setStatus("uploading");
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    const intent = await getCarrosselFotoUploadIntent(ext);
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
      const finalUrl = intent.publicUrl;
      setUrl(finalUrl);
      setStatus("ok");
      const saved = await salvarSlideFotoAction(carrosselId, slideIdx, finalUrl);
      if (!saved.ok) {
        setStatus("error");
        setErrorMsg(`Foto enviada, mas falhou ao salvar: ${saved.error}`);
      }
    } catch (e) {
      setStatus("error");
      setErrorMsg(e instanceof Error ? e.message : "Falha desconhecida.");
    }
  }

  async function handleRemove() {
    setStatus("uploading");
    const saved = await salvarSlideFotoAction(carrosselId, slideIdx, "");
    if (saved.ok) {
      setUrl("");
      setStatus("idle");
    } else {
      setStatus("error");
      setErrorMsg(saved.error);
    }
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border border-onix-100 bg-white p-3">
      <div
        className="w-16 h-20 rounded border border-onix-100 bg-onix-50 bg-center bg-no-repeat bg-cover shrink-0"
        style={url ? { backgroundImage: `url("${url}")` } : undefined}
      />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-semibold text-onix-900">
          Slide {slideIdx + 1}
        </div>
        <div className="text-[10px] text-g60 mt-0.5">
          {status === "ok"
            ? "Foto pronta"
            : status === "uploading"
              ? "Enviando…"
              : status === "error"
                ? errorMsg
                : "Sem foto (usa fundo padrão do tema)"}
        </div>
        <div className="flex items-center gap-2 mt-1.5">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            disabled={status === "uploading"}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void handleFile(f);
            }}
            className="block text-[11px] text-onix-800 file:mr-2 file:rounded file:border file:border-onix-100 file:bg-onix-50 file:px-2 file:py-1 file:text-[11px] file:font-medium hover:file:bg-onix-100 disabled:opacity-50"
          />
          {status === "ok" && (
            <button
              type="button"
              onClick={handleRemove}
              className="text-[11px] text-red-700 hover:underline"
            >
              Remover
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
