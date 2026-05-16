"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { regenerarCopiesAction } from "../../actions";

/** Quando a /copy page abre e copy_options ta vazio, dispara a geracao
 *  client-side com timeout proprio (40s). Server action nao precisa
 *  esperar OpenAI dentro do iniciarCarrosselAction (estourava o cap
 *  de 26s do Netlify Functions). */
export function AutoGenerateCopies({ carrosselId }: { carrosselId: string }) {
  const fired = useRef(false);
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    if (fired.current) return;
    fired.current = true;
    void (async () => {
      try {
        await regenerarCopiesAction(carrosselId);
        // server action redireciona; force refresh por garantia
        router.refresh();
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Falha desconhecida ao gerar copy.",
        );
      }
    })();
  }, [carrosselId, router]);

  return (
    <div className="rounded-xl border border-mint-200 bg-mint-50 px-5 py-6 text-sm text-mint-900">
      {error ? (
        <>
          <strong>Falha na geração:</strong> {error}
          <br />
          Tente clicar em &quot;↻ Gerar 3 opções novas&quot; quando aparecer.
        </>
      ) : (
        <>
          <strong>Gerando 3 opções de copy…</strong> Isso leva 10–20 segundos.
          A página atualiza sozinha.
        </>
      )}
    </div>
  );
}
