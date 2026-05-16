import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";

export default async function SindicompanyHome() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (verifySessionToken(token)) {
    redirect("/sindicompany/dashboard");
  }
  redirect("/sindicompany/login");
}
