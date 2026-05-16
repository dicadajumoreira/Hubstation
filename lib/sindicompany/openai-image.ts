/**
 * Geração de imagens via DALL-E 3 (OpenAI). Usado pra criar a foto da
 * capa do carrossel Instagram a partir do briefing da editora — quando
 * ela não quer fazer upload manual.
 *
 * Não usa SDK pra evitar dependência adicional; chama a REST API direto.
 */

const OPENAI_API = "https://api.openai.com/v1/images/generations";

export interface DalleResult {
  ok: true;
  /** Bytes da imagem ja decodificados (PNG). Sempre presente; pronto pra
   *  upload no Storage sem precisar baixar de uma URL temporaria. */
  bytes: Buffer;
  /** URL temporaria — so e preenchida no modo legado dall-e-3 com
   *  response_format=url. Preferir `bytes`. */
  url?: string;
  /** Prompt revisado pela OpenAI (eles ajustam pra moderation/quality). */
  revised_prompt?: string;
}

export interface DalleError {
  ok: false;
  error: string;
}

interface DalleOptions {
  /** "1024x1024" (quadrada), "1792x1024" / "1536x1024" (landscape) ou
   *  "1024x1792" / "1024x1536" (portrait). O codigo normaliza pro modelo
   *  ativo automaticamente. */
  size?: "1024x1024" | "1792x1024" | "1024x1792" | "1536x1024" | "1024x1536" | "auto";
  /** Qualidade. "standard"/"hd" sao do dall-e-3; "low"/"medium"/"high"/"auto"
   *  sao do gpt-image-1. Mapeado automaticamente. */
  quality?: "standard" | "hd" | "low" | "medium" | "high" | "auto";
  /** Apenas dall-e-3. Ignorado por gpt-image-1. */
  style?: "vivid" | "natural";
}

/** Modelo padrao: dall-e-3 (estavel e disponivel pra contas sem
 *  verificacao de organizacao). Pra usar gpt-image-1 (mais moderno mas
 *  exige verificacao), defina OPENAI_IMAGE_MODEL=gpt-image-1 na env. */
function _imageModel(): string {
  return (process.env.OPENAI_IMAGE_MODEL || "dall-e-3").trim();
}

function _mapSizeForModel(size: string, model: string): string {
  if (model.startsWith("dall-e")) {
    // dall-e-3 aceita: 1024x1024, 1792x1024, 1024x1792.
    if (size === "1536x1024") return "1792x1024";
    if (size === "1024x1536") return "1024x1792";
    if (size === "auto") return "1024x1024";
    return size;
  }
  // gpt-image-1 aceita: 1024x1024, 1536x1024, 1024x1536, auto.
  if (size === "1792x1024") return "1536x1024";
  if (size === "1024x1792") return "1024x1536";
  return size;
}

function _mapQualityForModel(q: string | undefined, model: string): string {
  if (!q) return model.startsWith("dall-e") ? "hd" : "high";
  if (model.startsWith("dall-e")) {
    if (q === "high") return "hd";
    if (q === "medium" || q === "low") return "standard";
    if (q === "auto") return "hd";
    return q;
  }
  // gpt-image-1
  if (q === "hd") return "high";
  if (q === "standard") return "medium";
  return q;
}

export async function generateImage(
  prompt: string,
  opts: DalleOptions = {},
): Promise<DalleResult | DalleError> {
  // Sanitiza a chave: trim de whitespace/quebras de linha + remove
  // prefixo 'Bearer ' se a editora colou já com header.
  const rawKey = (process.env.OPENAI_API_KEY ?? "").trim();
  const apiKey = rawKey.replace(/^Bearer\s+/i, "");
  if (!apiKey) {
    return { ok: false, error: "OPENAI_API_KEY ausente nas variáveis de ambiente." };
  }
  if (!apiKey.startsWith("sk-")) {
    return {
      ok: false,
      error: "OPENAI_API_KEY não começa com 'sk-' (formato inválido). Verifique a variável no Vercel.",
    };
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${apiKey}`,
  };
  // Project keys (sk-proj-...) podem exigir org/project explícito
  // dependendo da config da conta. Se as envs estiverem setadas,
  // anexa.
  const orgId = (process.env.OPENAI_ORGANIZATION ?? "").trim();
  if (orgId) headers["OpenAI-Organization"] = orgId;
  const projId = (process.env.OPENAI_PROJECT ?? "").trim();
  if (projId) headers["OpenAI-Project"] = projId;

  // Tenta o modelo configurado e, em caso de falha, tenta o outro
  // (dall-e-3 <-> gpt-image-1). Cobre contas com acesso so a um deles.
  const primario = _imageModel();
  const alt = primario === "dall-e-3" ? "gpt-image-1" : "dall-e-3";
  const candidatos = Array.from(new Set([primario, alt]));

  let ultimoErro = "OpenAI falhou em todos os modelos disponíveis.";

  for (const model of candidatos) {
    const size = _mapSizeForModel(opts.size ?? "1024x1792", model);
    const quality = _mapQualityForModel(opts.quality, model);
    const body: Record<string, unknown> = {
      model,
      prompt,
      n: 1,
      size,
      quality,
    };
    if (model.startsWith("dall-e")) {
      body.style = opts.style ?? "natural";
      body.response_format = "url";
    }
    // gpt-image-1 sempre retorna b64_json; sem response_format.

    let res: Response;
    try {
      res = await fetch(OPENAI_API, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
    } catch (e) {
      ultimoErro = e instanceof Error ? `Falha de rede (${model}): ${e.message}` : `Falha de rede (${model}).`;
      console.error("[openai-image]", ultimoErro);
      continue;
    }

    if (!res.ok) {
      let detail = "";
      try {
        const j = await res.json();
        detail = j?.error?.message ?? JSON.stringify(j);
      } catch {
        detail = await res.text().catch(() => "");
      }
      if (res.status === 401) {
        const isProjKey = apiKey.startsWith("sk-proj-");
        const dica = isProjKey
          ? "Sua chave é do tipo 'project' (sk-proj-...). Defina também as variáveis OPENAI_PROJECT (proj_...) e/ou OPENAI_ORGANIZATION (org_...) no Vercel."
          : "Verifique se OPENAI_API_KEY está correta no Vercel (sem espaços, sem aspas) e se a conta tem créditos.";
        // 401 e auth — nao adianta tentar outro modelo, devolve direto.
        return {
          ok: false,
          error: `OpenAI 401 (auth inválida): ${detail.slice(0, 160)}. ${dica}`,
        };
      }
      ultimoErro = `${model} retornou ${res.status}: ${detail.slice(0, 200)}`;
      console.error("[openai-image]", ultimoErro);
      // 403/400 podem ser "model not available" -> tenta o proximo.
      continue;
    }

    let json: { data?: Array<{ url?: string; b64_json?: string; revised_prompt?: string }> };
    try {
      json = await res.json();
    } catch {
      ultimoErro = `${model}: OpenAI retornou resposta não-JSON.`;
      continue;
    }

    const item = json.data?.[0];
    if (!item) {
      ultimoErro = `${model}: resposta sem dados de imagem.`;
      continue;
    }
    if (item.b64_json) {
      try {
        const bytes = Buffer.from(item.b64_json, "base64");
        return { ok: true, bytes, revised_prompt: item.revised_prompt };
      } catch (e) {
        ultimoErro = `${model}: falha ao decodificar b64_json: ${e instanceof Error ? e.message : String(e)}`;
        continue;
      }
    }
    if (item.url) {
      try {
        const bytes = await downloadImageBytes(item.url);
        return { ok: true, bytes, url: item.url, revised_prompt: item.revised_prompt };
      } catch (e) {
        ultimoErro = `${model}: falha ao baixar imagem: ${e instanceof Error ? e.message : String(e)}`;
        continue;
      }
    }
    ultimoErro = `${model}: resposta sem url nem b64_json.`;
  }

  return { ok: false, error: ultimoErro };
}

/** Baixa a imagem temporária da OpenAI e devolve os bytes. URL da OpenAI
 *  expira em ~1h, então sempre re-upload pra Supabase. */
export async function downloadImageBytes(url: string): Promise<Buffer> {
  const res = await fetch(url, {
    headers: { "User-Agent": "sindicompany-painel/1.0" },
  });
  if (!res.ok) {
    throw new Error(`Download da imagem falhou: HTTP ${res.status}`);
  }
  const ab = await res.arrayBuffer();
  return Buffer.from(ab);
}

/** Constrói um prompt editorial pra DALL-E baseado no briefing do
 *  carrossel. O estilo é fotojornalismo brasileiro de condomínio
 *  (real, sem ilustração, sem texto na imagem). */
export function buildCarrosselPrompt(input: {
  titulo: string;
  tema?: string | null;
  formato?: string | null;
  briefing?: string | null;
}): string {
  const partes = [
    "Editorial photograph for Brazilian Instagram carousel cover (4:5 vertical).",
    `Subject/theme: ${_sanitizar(input.tema ?? input.titulo)}.`,
  ];
  if (input.formato) partes.push(`Format: ${input.formato.replaceAll("_", " ")}.`);
  if (input.briefing) {
    const brief = _sanitizar(input.briefing).slice(0, 500);
    partes.push(`Context/briefing: ${brief}`);
  }
  partes.push(
    "Style: candid documentary photography, real Brazilian condominium setting (lobby, hallway, common area, garden, balcony as appropriate). Natural daylight, shallow depth of field, journalistic framing. People are diverse (when present), in everyday moments, no posing. Cinematic warm tones. Photorealistic, hyper-detailed, no illustration, no graphic art, NO TEXT IN THE IMAGE, no logos, no watermarks. Composition leaves the bottom half slightly less busy so a text overlay can be added later in post-production.",
  );
  return partes.join(" ");
}

/** Versão minimal do prompt — usada como fallback quando a OpenAI
 *  rejeita o prompt completo por safety. Remove o briefing
 *  (provável fonte do trigger) e fica genérico. */
export function buildCarrosselPromptSafe(input: {
  titulo: string;
  tema?: string | null;
}): string {
  const tema = _sanitizar(input.tema ?? input.titulo);
  return (
    `Editorial photograph for Brazilian Instagram cover (4:5 vertical). ` +
    `Subject: ${tema}. ` +
    `Style: candid documentary photo, real Brazilian residential building setting, ` +
    `natural daylight, shallow depth of field, photorealistic, no text, no logos. ` +
    `Color palette dominated by Sindicompany brand pastels: mint cyan #84C7D3, ` +
    `warm sand beige #DABDA9, soft lavender #B8C0FF, white #FFFFFF, light gray ` +
    `#F4F4F5. Airy and low-saturation. Avoid heavy reds, oranges, dark blues, ` +
    `forest greens or saturated primaries.`
  );
}

/** Substitui termos que costumam disparar o safety filter da OpenAI
 *  por sinônimos mais neutros (sem perder o sentido pra um prompt
 *  de fotografia editorial). */
function _sanitizar(s: string): string {
  if (!s) return "";
  const map: Array<[RegExp, string]> = [
    [/\bseguran[çc]a\b/gi, "comunidade"],
    [/\bconflito(s)?\b/gi, "convivência"],
    [/\bbriga(s)?\b/gi, "diálogo"],
    [/\bviol[êe]ncia\b/gi, "atenção"],
    [/\barma(s)?\b/gi, ""],
    [/\bdroga(s)?\b/gi, ""],
    [/\bcrime(s)?\b/gi, "questão"],
    [/\binadimpl[êe]ncia\b/gi, "gestão financeira"],
    [/\bd[ií]vida(s)?\b/gi, "compromisso"],
  ];
  let out = s;
  for (const [re, repl] of map) out = out.replace(re, repl);
  return out;
}
