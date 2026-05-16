"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  SESSION_COOKIE,
  SESSION_MAX_AGE,
  createSessionToken,
  verifyPassword,
} from "@/lib/sindicompany/auth";

export async function loginAction(formData: FormData) {
  const password = String(formData.get("password") ?? "").trim();
  if (!password) {
    return { error: "Informe a senha." };
  }
  if (!verifyPassword(password)) {
    // Pequeno delay constante para reduzir timing attacks brutos
    await new Promise((r) => setTimeout(r, 250));
    return { error: "Senha incorreta." };
  }
  const store = await cookies();
  store.set(SESSION_COOKIE, createSessionToken(), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    // path "/" para que o cookie chegue também em /api/sindicompany/*
    // (rota que serve o PDF assinado)
    path: "/",
    maxAge: SESSION_MAX_AGE,
  });
  redirect("/sindicompany/dashboard");
}

export async function logoutAction() {
  const store = await cookies();
  store.delete(SESSION_COOKIE);
  redirect("/sindicompany/login");
}
