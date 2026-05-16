"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

interface CondoSelectProps {
  condominios: readonly string[];
  defaultValue: string;
  className: string;
}

/**
 * Select de condomínio que recarrega a página com `?condominio=X`
 * quando muda, pra que o server saiba qual condo está selecionado e
 * possa mostrar/esconder a seção do gestor de acordo com o cadastro.
 */
export function CondoSelect({ condominios, defaultValue, className }: CondoSelectProps) {
  const router = useRouter();
  const params = useSearchParams();
  const [isPending, startTransition] = useTransition();

  function onChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const next = new URLSearchParams(params?.toString() ?? "");
    if (e.target.value) {
      next.set("condominio", e.target.value);
    } else {
      next.delete("condominio");
    }
    startTransition(() => {
      router.replace(`?${next.toString()}`, { scroll: false });
    });
  }

  return (
    <select
      name="condominio"
      required
      defaultValue={defaultValue}
      onChange={onChange}
      disabled={isPending}
      className={className}
    >
      <option value="">Selecione…</option>
      {condominios.map((c) => (
        <option key={c} value={c}>{c}</option>
      ))}
    </select>
  );
}

interface MesSelectProps {
  meses: readonly string[];
  defaultValue: string;
  className: string;
}

/** Select de mês que sincroniza ?mes=MM na URL pra puxar o editorial. */
export function MesSelect({ meses, defaultValue, className }: MesSelectProps) {
  const router = useRouter();
  const params = useSearchParams();
  const [isPending, startTransition] = useTransition();

  function onChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const next = new URLSearchParams(params?.toString() ?? "");
    next.set("mes", e.target.value);
    startTransition(() => {
      router.replace(`?${next.toString()}`, { scroll: false });
    });
  }

  return (
    <select
      name="mes"
      required
      defaultValue={defaultValue}
      onChange={onChange}
      disabled={isPending}
      className={className}
    >
      {meses.map((m, i) => (
        <option key={m} value={String(i + 1).padStart(2, "0")}>{m}</option>
      ))}
    </select>
  );
}

interface AnoInputProps {
  defaultValue: number;
  className: string;
}

/** Input de ano que sincroniza ?ano=YYYY na URL no blur. */
export function AnoInput({ defaultValue, className }: AnoInputProps) {
  const router = useRouter();
  const params = useSearchParams();
  const [isPending, startTransition] = useTransition();

  function commit(value: string) {
    const n = Number.parseInt(value, 10);
    if (!Number.isInteger(n) || n < 2025 || n > 2030) return;
    const next = new URLSearchParams(params?.toString() ?? "");
    next.set("ano", String(n));
    startTransition(() => {
      router.replace(`?${next.toString()}`, { scroll: false });
    });
  }

  return (
    <input
      type="number"
      name="ano"
      defaultValue={defaultValue}
      min={2025}
      max={2030}
      required
      disabled={isPending}
      onBlur={(e) => commit(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          commit((e.target as HTMLInputElement).value);
        }
      }}
      className={className + " tabular-nums"}
    />
  );
}
