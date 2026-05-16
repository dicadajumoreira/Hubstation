import { NextResponse, type NextRequest } from "next/server";
import { resolveTenantFromHost } from "@/lib/tenant";
import { updateSession } from "@/lib/supabase/middleware";

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|api/|.*\\..*).*)",
  ],
};

export async function middleware(request: NextRequest) {
  const sessionResponse = await updateSession(request);

  const host = request.headers.get("host");
  const tenant = resolveTenantFromHost(host);

  if (tenant.kind === "tenant") {
    const url = request.nextUrl.clone();
    if (url.pathname.startsWith("/condo/")) {
      return sessionResponse;
    }
    url.pathname = `/condo/${tenant.slug}${url.pathname === "/" ? "" : url.pathname}`;
    const rewrite = NextResponse.rewrite(url, { request });
    sessionResponse.cookies.getAll().forEach((c) => {
      rewrite.cookies.set(c.name, c.value);
    });
    return rewrite;
  }

  if (tenant.kind === "sindicompany") {
    const url = request.nextUrl.clone();
    if (url.pathname.startsWith("/sindicompany")) {
      return sessionResponse;
    }
    url.pathname = `/sindicompany${url.pathname === "/" ? "" : url.pathname}`;
    const rewrite = NextResponse.rewrite(url, { request });
    sessionResponse.cookies.getAll().forEach((c) => {
      rewrite.cookies.set(c.name, c.value);
    });
    return rewrite;
  }

  return sessionResponse;
}
