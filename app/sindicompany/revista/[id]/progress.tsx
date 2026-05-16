"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface ProgressProps {
  createdAt: string;       // ISO string
  expectedSeconds?: number; // tempo típico de geração (90s default)
  warnAfterSeconds?: number; // mostra alerta de "engine offline"
}

/**
 * Progresso simulado pra revistas em produção. Como a engine ainda
 * não cravava progresso real, usamos o tempo decorrido como estimativa.
 *
 * - Avança até 95% no tempo esperado, depois trava ali (porque quem
 *   sabe é o backend).
 * - A página recarrega a cada 5s pra pegar mudança real de status.
 * - Após `warnAfterSeconds`, mostra aviso de que algo pode estar
 *   travado (engine offline, etc).
 */
export function RevistaProgress({
  createdAt,
  expectedSeconds = 90,
  warnAfterSeconds = 180,
}: ProgressProps) {
  const router = useRouter();
  const [elapsed, setElapsed] = useState(() =>
    Math.max(0, (Date.now() - new Date(createdAt).getTime()) / 1000),
  );

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((Date.now() - new Date(createdAt).getTime()) / 1000);
    }, 1000);
    return () => clearInterval(interval);
  }, [createdAt]);

  // Refresh server data a cada 5s
  useEffect(() => {
    const refresh = setInterval(() => {
      router.refresh();
    }, 5000);
    return () => clearInterval(refresh);
  }, [router]);

  const pct = Math.min(95, (elapsed / expectedSeconds) * 95);
  const stuck = elapsed > warnAfterSeconds;

  function fmt(seconds: number): string {
    const s = Math.floor(seconds);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}min ${String(r).padStart(2, "0")}s`;
  }

  const restanteEstimado = Math.max(0, expectedSeconds - elapsed);

  return (
    <div className="space-y-3">
      <div className="rounded-lg bg-onix-50 px-4 py-3 text-sm">
        <div className="flex items-center justify-between mb-2">
          <strong className="text-onix-900">
            {stuck ? "Aguardando engine…" : "A engine está montando a revista"}
          </strong>
          <span className="text-xs text-g60 tabular-nums">
            {fmt(elapsed)}
            {!stuck && (
              <>
                {" "}· ~{fmt(restanteEstimado)} restante
              </>
            )}
          </span>
        </div>

        {/* Barra */}
        <div className="h-2 rounded-full bg-onix-100 overflow-hidden">
          <div
            className={`h-full transition-all duration-1000 ease-linear ${
              stuck ? "bg-amber-400" : "bg-mint-600"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>

        <div className="mt-2 text-xs text-g60">
          {stuck
            ? "Está demorando mais que o esperado. A engine pode estar offline."
            : "A página atualiza sozinha quando a revista ficar pronta."}
        </div>
      </div>

      {stuck && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <strong>Heads up:</strong> a engine Python que renderiza o PDF
          ainda não está conectada ao site. O registro foi salvo no banco,
          mas nenhum serviço está processando ainda. Você pode marcar como
          erro pra liberar o slot.
        </div>
      )}
    </div>
  );
}
