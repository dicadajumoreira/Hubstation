"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Auto-refresh client-side a cada 6s enquanto o carrossel está em
 *  produção. Desligar quando pronto/erro evita polling infinito. */
export function CarrosselAutoRefresh({ active }: { active: boolean }) {
  const router = useRouter();
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => router.refresh(), 6000);
    return () => clearInterval(id);
  }, [active, router]);
  return null;
}
