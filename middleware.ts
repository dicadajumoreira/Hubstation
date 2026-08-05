import { NextResponse, type NextRequest } from "next/server";
import { resolveTenantFromHost } from "@/lib/tenant";
import { updateSession } from "@/lib/supabase/middleware";

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|api/|.*\\..*).*)",
    // O padrão acima ignora qualquer path com ponto. Estes precisam passar
    // pelo middleware por causa do site da HubStation (ver hubstationSite).
    "/sitemap.xml",
    "/robots.txt",
    "/index.html",
    "/sobre.html",
    "/servicos.html",
    "/eventos.html",
    "/blog.html",
    "/contato.html",
  ],
};

/** Páginas do site institucional da HubStation, em public/hubstation/. */
const HUBSTATION_PAGES = new Set([
  "index",
  "sobre",
  "servicos",
  "eventos",
  "blog",
  "contato",
]);

/**
 * hubstation.com.br é servido a partir dos arquivos estáticos em
 * public/hubstation/. O site é público — não passa pelo updateSession
 * do Supabase, pra não criar sessão nem cookie em visitante de site
 * institucional.
 */
function hubstationSite(request: NextRequest): NextResponse {
  const url = request.nextUrl.clone();
  const { pathname } = url;

  // URLs antigas com .html continuam indexadas no Google (o site anterior
  // servia /sobre.html). 301 pra versão limpa preserva o ranqueamento.
  if (pathname.endsWith(".html")) {
    const slug = pathname.slice(1, -".html".length);
    if (HUBSTATION_PAGES.has(slug)) {
      url.pathname = slug === "index" ? "/" : `/${slug}`;
      return NextResponse.redirect(url, 301);
    }
    return NextResponse.next();
  }

  if (pathname === "/sitemap.xml" || pathname === "/robots.txt") {
    url.pathname = `/hubstation${pathname}`;
    return NextResponse.rewrite(url);
  }

  const slug = pathname === "/" ? "index" : pathname.replace(/^\/+|\/+$/g, "");
  if (HUBSTATION_PAGES.has(slug)) {
    url.pathname = `/hubstation/${slug}.html`;
    return NextResponse.rewrite(url);
  }

  // Path desconhecido: deixa o Next responder 404 de verdade (um rewrite
  // pra home aqui viraria soft 404 e o Google penaliza).
  return NextResponse.next();
}

export async function middleware(request: NextRequest) {
  const host = request.headers.get("host");
  const tenant = resolveTenantFromHost(host);

  if (tenant.kind === "hubstation") {
    return hubstationSite(request);
  }

  const sessionResponse = await updateSession(request);

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
