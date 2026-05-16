"use client";

import { useState, useTransition } from "react";
import { loginAction } from "./actions";

export default function LoginPage() {
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <main className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-10">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="https://raw.githubusercontent.com/dicadajumoreira/Sindicompany/main/Logotipo%20Sindicompany%201.png"
            alt="Sindicompany"
            className="h-10 w-auto mx-auto mb-4"
          />
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-3">
            Comunicação
          </div>
          <h1 className="text-3xl font-bold text-onix-900 leading-none">
            Entrar na plataforma
          </h1>
          <p className="text-sm text-g60 mt-3">
            Acesso restrito à equipe editorial.
          </p>
        </div>

        <form
          className="space-y-4"
          action={(fd) => {
            setError(null);
            start(async () => {
              const res = await loginAction(fd);
              if (res?.error) setError(res.error);
            });
          }}
        >
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-wider text-onix-800">
              Senha
            </span>
            <input
              type="password"
              name="password"
              required
              autoFocus
              autoComplete="current-password"
              className="mt-1.5 block w-full rounded-lg border border-onix-100 bg-white px-3.5 py-2.5 text-onix-900 outline-none focus:border-mint-600 focus:ring-2 focus:ring-mint-100"
              disabled={pending}
            />
          </label>

          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-3.5 py-2.5 text-sm text-red-800">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-lg bg-onix-900 text-white px-4 py-2.5 font-medium hover:bg-onix-800 disabled:opacity-60"
          >
            {pending ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <p className="text-center text-xs text-g60 mt-8">
          Esqueceu a senha? Fale com a Juliana.
        </p>
      </div>
    </main>
  );
}
