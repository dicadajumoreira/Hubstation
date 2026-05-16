"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import {
  getEventosZipUploadIntent,
  getManutencaoCapaUploadIntent,
  getManutencaoZipUploadIntent,
  getPrestacaoUploadIntent,
} from "./upload-actions";

type UploadKind = "prestacao" | "manutencao_zip" | "eventos_zip" | "manutencao_capa";

interface DirectUploadFieldProps {
  kind: UploadKind;
  /** Nome do <input hidden> que carrega a URL final no submit do form. */
  hiddenInputName: string;
  /** URL inicial (caso a edição venha duplicada). */
  initialUrl?: string;
  accept: string;
  maxBytes: number;
}

/** Lê o valor atual do select <input name="condominio"> no form pai. */
function getCondominioFromForm(el: HTMLElement | null): string {
  let cur: HTMLElement | null = el;
  while (cur && cur.tagName !== "FORM") cur = cur.parentElement;
  if (!cur) return "";
  const form = cur as HTMLFormElement;
  const raw = (new FormData(form)).get("condominio");
  return typeof raw === "string" ? raw.trim() : "";
}

const BUCKET = "condominios-fotos";

export function DirectUploadField({
  kind,
  hiddenInputName,
  initialUrl,
  accept,
  maxBytes,
}: DirectUploadFieldProps) {
  const [url, setUrl] = useState(initialUrl ?? "");
  const [status, setStatus] = useState<"idle" | "uploading" | "ok" | "error">(
    initialUrl ? "ok" : "idle",
  );
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [filename, setFilename] = useState("");

  async function handleFile(file: File, inputEl: HTMLInputElement) {
    setErrorMsg("");
    setFilename(file.name);

    if (file.size > maxBytes) {
      const limitMb = Math.round(maxBytes / (1024 * 1024));
      setStatus("error");
      setErrorMsg(`Arquivo maior que ${limitMb}MB.`);
      return;
    }

    const condominio = getCondominioFromForm(inputEl);
    if (!condominio) {
      setStatus("error");
      setErrorMsg("Selecione o condomínio primeiro (campo no topo do form).");
      return;
    }

    setStatus("uploading");
    setProgress(0);

    // 1. Pede um signed upload URL ao servidor
    let intent;
    if (kind === "prestacao") {
      const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
      const r = await getPrestacaoUploadIntent(condominio, ext);
      if (!r.ok) {
        setStatus("error");
        setErrorMsg(r.error);
        return;
      }
      intent = r;
    } else if (kind === "manutencao_zip") {
      const r = await getManutencaoZipUploadIntent(condominio);
      if (!r.ok) {
        setStatus("error");
        setErrorMsg(r.error);
        return;
      }
      intent = r;
    } else if (kind === "manutencao_capa") {
      const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
      const r = await getManutencaoCapaUploadIntent(condominio, ext);
      if (!r.ok) {
        setStatus("error");
        setErrorMsg(r.error);
        return;
      }
      intent = r;
    } else {
      // eventos_zip
      const r = await getEventosZipUploadIntent(condominio);
      if (!r.ok) {
        setStatus("error");
        setErrorMsg(r.error);
        return;
      }
      intent = r;
    }

    // 2. Upload direto pro Supabase Storage usando o token assinado
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

      setUrl(intent.publicUrl);
      setProgress(100);
      setStatus("ok");
    } catch (e) {
      setStatus("error");
      setErrorMsg(e instanceof Error ? e.message : "Falha desconhecida.");
    }
  }

  return (
    <div className="space-y-2">
      {url && status === "ok" && (
        <div className="flex items-center gap-3 text-xs">
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-mint-700 underline underline-offset-2"
          >
            Ver arquivo enviado
          </a>
          <span className="text-g60">{filename || "Arquivo salvo. Suba outro pra trocar."}</span>
        </div>
      )}

      <input type="hidden" name={hiddenInputName} value={url} />

      <input
        type="file"
        accept={accept}
        disabled={status === "uploading"}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void handleFile(f, e.target);
        }}
        className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100 disabled:opacity-50"
      />

      {status === "uploading" && (
        <div className="space-y-1">
          <div className="text-xs text-g60">
            Enviando {filename}…
          </div>
          <div className="h-1.5 rounded-full bg-onix-100 overflow-hidden">
            <div
              className="h-full bg-mint-600 transition-all"
              style={{ width: `${progress || 25}%` }}
            />
          </div>
        </div>
      )}

      {status === "error" && (
        <div className="text-xs text-red-700">
          <strong>Erro:</strong> {errorMsg}
        </div>
      )}
    </div>
  );
}
