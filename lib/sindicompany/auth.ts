import crypto from "node:crypto";

const COOKIE_NAME = "sc_session";
const ONE_WEEK_S = 60 * 60 * 24 * 7;

function getSecret(): string {
  const s = process.env.SINDICOMPANY_COOKIE_SECRET;
  if (!s || s.length < 16) {
    throw new Error(
      "SINDICOMPANY_COOKIE_SECRET ausente ou muito curto (mínimo 16 caracteres). " +
      "Defina em .env.local."
    );
  }
  return s;
}

function getPassword(): string {
  const p = process.env.SINDICOMPANY_PASSWORD;
  if (!p) {
    throw new Error(
      "SINDICOMPANY_PASSWORD ausente. Defina em .env.local."
    );
  }
  return p;
}

/** Compara duas senhas em tempo constante. */
export function verifyPassword(input: string): boolean {
  const expected = getPassword();
  if (input.length !== expected.length) return false;
  return crypto.timingSafeEqual(
    Buffer.from(input, "utf8"),
    Buffer.from(expected, "utf8")
  );
}

/** Cria um token assinado: payload.signature em base64url. */
export function createSessionToken(): string {
  const issuedAt = Math.floor(Date.now() / 1000);
  const expiresAt = issuedAt + ONE_WEEK_S;
  const payload = JSON.stringify({ iat: issuedAt, exp: expiresAt });
  const payloadB64 = Buffer.from(payload).toString("base64url");
  const sig = crypto
    .createHmac("sha256", getSecret())
    .update(payloadB64)
    .digest("base64url");
  return `${payloadB64}.${sig}`;
}

/** Verifica token; retorna true se válido e não expirado. */
export function verifySessionToken(token: string | undefined): boolean {
  if (!token) return false;
  const [payloadB64, sig] = token.split(".");
  if (!payloadB64 || !sig) return false;

  const expectedSig = crypto
    .createHmac("sha256", getSecret())
    .update(payloadB64)
    .digest("base64url");

  let sigBuf: Buffer;
  let expBuf: Buffer;
  try {
    sigBuf = Buffer.from(sig, "base64url");
    expBuf = Buffer.from(expectedSig, "base64url");
  } catch {
    return false;
  }
  if (sigBuf.length !== expBuf.length) return false;
  if (!crypto.timingSafeEqual(sigBuf, expBuf)) return false;

  try {
    const payload = JSON.parse(Buffer.from(payloadB64, "base64url").toString("utf8"));
    if (typeof payload.exp !== "number") return false;
    return Math.floor(Date.now() / 1000) < payload.exp;
  } catch {
    return false;
  }
}

export const SESSION_COOKIE = COOKIE_NAME;
export const SESSION_MAX_AGE = ONE_WEEK_S;
