"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import {
  generateFotoCapaWithAI,
  getCarrosselFotoUploadIntent,
  salvarFotoCapaAction,
} from "./actions";

const BUCKET = "condominios-fotos";

export function CarrosselFotoUpload({
  carrosselId,
  initialUrl,
}: {
  carrosselId: string;
  initialUrl?: string;
}) {
  const [url, setUrl] = useState(initialUrl ?? "");
  const [status, setStatus] = useState<
    "idle" | "uploading" | "generating" | "ok" | "error"
  >(initialUrl ? "ok" : "idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [filename, setFilename] = useState("");
  const [revisedPrompt, setRevisedPrompt] = useState<string>("");
  const [userPrompt, setUserPrompt] = useState("");

  async function handleFile(file: File) {
    setErrorMsg("");
    setRevisedPrompt("");
    setFilename(file.name);
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
      setUrl(intent.publicUrl);
      setStatus("ok");
      const saved = await salvarFotoCapaAction(carrosselId, intent.publicUrl);
      if (!saved.ok) {
        setStatus("error");
        setErrorMsg(`Foto enviada, mas falhou ao salvar: ${saved.error}`);
      }
    } catch (e) {
      setStatus("error");
      setErrorMsg(e instanceof Error ? e.message : "Falha desconhecida.");
    }
  }

  async function handleGenerate() {
    setErrorMsg("");
    setRevisedPrompt("");
    setFilename("");
    setStatus("generating");

    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("timeout")), 40_000),
    );

    let result;
    try {
      result = await Promise.race([
        generateFotoCapaWithAI({
          carrosselId,
          userPrompt: userPrompt.trim() || undefined,
        }),
        timeoutPromise,
      ]);
    } catch (e) {
      setStatus("error");
      setErrorMsg(
        e instanceof Error && e.message === "timeout"
          ? "A geração demorou mais que 40s e foi interrompida. Tente de novo ou faça upload manual."
          : e instanceof Error
            ? e.message
            : "Falha desconhecida.",
      );
      return;
    }

    if (!result.ok) {
      setStatus("error");
      setErrorMsg(result.error);
      return;
    }
    setUrl(result.publicUrl);
    setRevisedPrompt(result.revisedPrompt ?? "");
    setStatus("ok");
  }

  const isBusy = status === "uploading" || status === "generating";

  return (
    <div className="space-y-3">
      {url && status === "ok" && (
        <div className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={url}
            alt="Foto da capa"
            className="w-32 rounded-lg object-cover bg-onix-50 border border-onix-100"
            style={{ aspectRatio: "4/5" }}
          />
          <div className="flex-1">
            <p className="text-xs text-mint-700 font-semibold">Foto pronta ✓</p>
            <p className="text-xs text-g60 mt-0.5">
              {filename || (revisedPrompt ? "Foto gerada por IA" : "")}
            </p>
            {revisedPrompt && (
              <p className="text-[10px] text-g60 mt-1 line-clamp-3">
                <em>{revisedPrompt}</em>
              </p>
            )}
          </div>
        </div>
      )}

      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          disabled={isBusy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleFile(f);
          }}
          className="block text-sm text-onix-800 file:mr-3 file:rounded-md file:border file:border-onix-100 file:bg-onix-50 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-onix-100 disabled:opacity-50"
        />
      </div>

      <div className="rounded-lg border border-onix-100 bg-onix-50/40 p-4 space-y-2">
        <label
          htmlFor="ai-prompt"
          className="block text-sm font-medium text-onix-900"
        >
          Descrever a imagem (opcional)
        </label>
        <p className="text-xs text-g60">
          Descreva a cena, ambiente, pessoas e clima. Se deixar vazio, a IA
          monta a cena a partir da copy escolhida. A imagem sai sempre
          ultra-realista, 8K.
        </p>
        <textarea
          id="ai-prompt"
          value={userPrompt}
          onChange={(e) => setUserPrompt(e.target.value)}
          rows={3}
          maxLength={600}
          placeholder="Ex: Mulher de 35 anos, sindica, no lobby de um predio brasileiro de classe media alta, luz natural pela manha, sorriso discreto, terno claro, segurando um tablet."
          disabled={isBusy}
          className="block w-full rounded-md border border-onix-100 bg-white px-3 py-2 text-sm text-onix-900 focus:outline-none focus:ring-2 focus:ring-mint-300 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={handleGenerate}
          disabled={isBusy}
          className="inline-flex items-center gap-1.5 rounded-md bg-mint-600 hover:bg-mint-700 text-white text-sm font-medium px-3 py-1.5 disabled:opacity-50"
        >
          ✨ Gerar com IA
        </button>
      </div>

      {status === "uploading" && <p className="text-xs text-g60">Enviando…</p>}
      {status === "generating" && (
        <p className="text-xs text-g60">
          Gerando imagem com IA usando a copy escolhida (até 30s)…
        </p>
      )}
      {status === "error" && (
        <p className="text-xs text-red-700">{errorMsg}</p>
      )}
    </div>
  );
}
