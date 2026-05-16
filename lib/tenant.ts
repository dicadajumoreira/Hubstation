const ROOT_DOMAIN = process.env.NEXT_PUBLIC_ROOT_DOMAIN ?? "sindico.info";
const SINDICOMPANY_DOMAIN = process.env.NEXT_PUBLIC_SINDICOMPANY_DOMAIN ?? "sindicompany.info";

const RESERVED_SUBDOMAINS = new Set([
  "www",
  "admin",
  "api",
  "app",
  "auth",
  "dashboard",
  "static",
  "cdn",
  "mail",
  "ftp",
]);

export type TenantContext =
  | { kind: "root" }
  | { kind: "tenant"; slug: string }
  | { kind: "sindicompany" };

export function resolveTenantFromHost(host: string | null): TenantContext {
  if (!host) return { kind: "root" };

  const cleanHost = host.split(":")[0].toLowerCase();

  // Sindicompany backoffice (separate domain)
  if (
    cleanHost === SINDICOMPANY_DOMAIN ||
    cleanHost === `www.${SINDICOMPANY_DOMAIN}` ||
    cleanHost === "sindicompany.localhost"
  ) {
    return { kind: "sindicompany" };
  }

  if (cleanHost === "localhost" || cleanHost === "127.0.0.1") {
    return { kind: "root" };
  }

  if (cleanHost === ROOT_DOMAIN || cleanHost === `www.${ROOT_DOMAIN}`) {
    return { kind: "root" };
  }

  const suffix = `.${ROOT_DOMAIN}`;
  if (cleanHost.endsWith(suffix)) {
    const sub = cleanHost.slice(0, -suffix.length);
    if (RESERVED_SUBDOMAINS.has(sub)) return { kind: "root" };
    if (!sub) return { kind: "root" };
    return { kind: "tenant", slug: sub };
  }

  if (cleanHost.endsWith(".netlify.app")) {
    return { kind: "root" };
  }

  return { kind: "root" };
}

export function isReservedSlug(slug: string): boolean {
  return RESERVED_SUBDOMAINS.has(slug.toLowerCase());
}
