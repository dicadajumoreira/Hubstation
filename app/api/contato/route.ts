import { NextResponse } from "next/server";

/**
 * Formulário de contato do site da HubStation (hubstation.com.br/contato).
 * Porte da antiga Netlify Function `netlify/functions/contato.mjs`.
 *
 * Dispara dois e-mails via Resend: notificação interna e agradecimento
 * pra quem preencheu.
 */

const CAMPOS = [
  "nome",
  "email",
  "empresa",
  "telefone",
  "segmento",
  "servico",
  "mensagem",
] as const;

type Campo = (typeof CAMPOS)[number];

const LIMITES: Record<Campo, number> = {
  nome: 120,
  email: 180,
  empresa: 160,
  telefone: 40,
  segmento: 120,
  servico: 160,
  mensagem: 5000,
};

/**
 * Tudo que vem do formulário entra em HTML de e-mail. Sem escape, dava pra
 * injetar link/markup no e-mail de agradecimento (que é enviado pra um
 * endereço escolhido por quem preenche o form) e usar o domínio da
 * HubStation como veículo de phishing.
 */
function esc(valor: string): string {
  return valor
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function linha(rotulo: string, valor: string, html = esc(valor)): string {
  return `<tr><td style="padding:11px 0;border-bottom:1px solid #eee;font-size:11px;color:#9A9A9A;text-transform:uppercase;letter-spacing:0.1em;width:130px">${rotulo}</td><td style="padding:11px 0;border-bottom:1px solid #eee;font-size:15px">${html}</td></tr>`;
}

export async function POST(request: Request) {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "JSON inválido" }, { status: 400 });
  }

  const dados = {} as Record<Campo, string>;
  for (const campo of CAMPOS) {
    const bruto = body[campo];
    const valor = typeof bruto === "string" ? bruto.trim() : "";
    if (valor.length > LIMITES[campo]) {
      return NextResponse.json(
        { error: `Campo "${campo}" excede o tamanho permitido` },
        { status: 400 },
      );
    }
    dados[campo] = valor;
  }

  const { nome, email, empresa, telefone, segmento, servico, mensagem } = dados;

  if (!nome || !email || !mensagem) {
    return NextResponse.json(
      { error: "Campos obrigatórios ausentes" },
      { status: 400 },
    );
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
    return NextResponse.json({ error: "E-mail inválido" }, { status: 400 });
  }

  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    console.error("RESEND_API_KEY não configurada");
    return NextResponse.json(
      { error: "Configuração de e-mail ausente" },
      { status: 500 },
    );
  }

  const primeiroNome = nome.split(" ")[0];

  const htmlInterno = `<div style="font-family:sans-serif;max-width:600px;margin:0 auto">
    <div style="background:#060606;padding:32px 40px">
      <h1 style="color:#fff;font-size:20px;margin:0 0 4px">HubStation</h1>
      <p style="color:rgba(255,255,255,0.4);font-size:10px;margin:0;letter-spacing:0.12em;text-transform:uppercase">Novo formulário de contato</p>
    </div>
    <div style="height:3px;background:#F44336"></div>
    <div style="background:#FAFAF8;padding:36px 40px;border:1px solid #e8e6e1;border-top:none">
      <table style="width:100%;border-collapse:collapse">
        ${linha("Nome", nome)}
        ${linha("E-mail", email, `<a href="mailto:${encodeURIComponent(email)}" style="color:#F44336">${esc(email)}</a>`)}
        ${empresa ? linha("Empresa", empresa) : ""}
        ${telefone ? linha("Telefone", telefone) : ""}
        ${segmento ? linha("Segmento", segmento) : ""}
        ${servico ? linha("Interesse", servico) : ""}
      </table>
      <div style="margin-top:24px;padding:20px 24px;background:#fff;border:1px solid #e8e6e1;border-left:3px solid #F44336">
        <p style="font-size:10px;color:#9A9A9A;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px">Mensagem</p>
        <p style="font-size:14px;line-height:1.75;margin:0">${esc(mensagem).replace(/\n/g, "<br>")}</p>
      </div>
    </div>
    <div style="background:#F5F3EE;padding:16px 40px;text-align:center">
      <p style="font-size:10px;color:#bbb;margin:0">HubStation · <a href="https://hubstation.com.br" style="color:#F44336">hubstation.com.br</a></p>
    </div>
  </div>`;

  const htmlAgradecimento = `<div style="font-family:sans-serif;max-width:560px;margin:0 auto">
    <div style="background:#060606;padding:40px 40px 32px">
      <div style="margin-bottom:20px"><span style="font-size:20px;font-weight:700;color:#fff">HUBSTATION</span></div>
      <h1 style="color:#fff;font-size:26px;font-weight:600;margin:0 0 12px;line-height:1.2">Obrigado pelo contato, ${esc(primeiroNome)}!</h1>
      <p style="color:rgba(255,255,255,0.5);font-size:15px;margin:0;line-height:1.65">Recebemos o seu cadastro. Nossa equipe entrará em contato o mais breve possível.</p>
    </div>
    <div style="height:3px;background:#F44336"></div>
    <div style="background:#FAFAF8;padding:36px 40px;border:1px solid #e8e6e1;border-top:none">
      <p style="font-size:15px;color:#4A4A4A;line-height:1.75;margin:0 0 28px">Agradecemos o seu interesse na <strong>HubStation</strong>. Analisaremos o contexto da sua marca e retornaremos em breve com as melhores alternativas para a sua comunicação no mercado condominial.</p>
      ${
        empresa || segmento || servico
          ? `<div style="background:#fff;border:1px solid #e8e6e1;border-left:3px solid #F44336;padding:20px 24px;margin-bottom:28px">
        <p style="font-size:10px;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;color:#9A9A9A;margin:0 0 12px">Seu cadastro em resumo</p>
        ${empresa ? `<p style="margin:0 0 6px;font-size:13px;color:#4A4A4A"><strong>Empresa:</strong> ${esc(empresa)}</p>` : ""}
        ${segmento ? `<p style="margin:0 0 6px;font-size:13px;color:#4A4A4A"><strong>Segmento:</strong> ${esc(segmento)}</p>` : ""}
        ${servico ? `<p style="margin:0;font-size:13px;color:#4A4A4A"><strong>Interesse:</strong> ${esc(servico)}</p>` : ""}
      </div>`
          : ""
      }
      <div style="background:#060606;padding:24px 28px;margin-bottom:28px">
        <p style="font-size:10px;letter-spacing:0.16em;text-transform:uppercase;color:rgba(255,255,255,0.35);margin:0 0 14px">O que acontece agora</p>
        <div style="display:flex;gap:14px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06)">
          <div style="width:20px;height:20px;border-radius:50%;background:#F44336;color:#fff;font-size:10px;font-weight:700;text-align:center;line-height:20px;flex-shrink:0">1</div>
          <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.55);line-height:1.55">Lemos seu cadastro e analisamos o contexto da sua marca</p>
        </div>
        <div style="display:flex;gap:14px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06)">
          <div style="width:20px;height:20px;border-radius:50%;border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.4);font-size:10px;font-weight:700;text-align:center;line-height:18px;flex-shrink:0">2</div>
          <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.55);line-height:1.55">Nossa equipe entra em contato o mais breve possível</p>
        </div>
        <div style="display:flex;gap:14px;padding:10px 0">
          <div style="width:20px;height:20px;border-radius:50%;border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.4);font-size:10px;font-weight:700;text-align:center;line-height:18px;flex-shrink:0">3</div>
          <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.55);line-height:1.55">Apresentamos um caminho real para a comunicação da sua marca</p>
        </div>
      </div>
      <div style="text-align:center">
        <a href="https://hubstation.com.br/servicos" style="display:inline-block;background:#F44336;color:#fff;text-decoration:none;font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;padding:14px 30px">Conheça nossos serviços →</a>
      </div>
    </div>
    <div style="background:#F5F3EE;padding:18px 40px;text-align:center">
      <p style="font-size:11px;color:#9A9A9A;margin:0 0 3px"><a href="https://hubstation.com.br" style="color:#F44336">hubstation.com.br</a> · <a href="https://instagram.com/hubstationbr" style="color:#9A9A9A">@hubstationbr</a></p>
      <p style="font-size:10px;color:#ccc;margin:0">Você recebeu este e-mail porque preencheu o formulário de contato da HubStation.</p>
    </div>
  </div>`;

  const enviar = (payload: Record<string, unknown>) =>
    fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

  try {
    const [notifResp, confirmResp] = await Promise.all([
      enviar({
        from: "HubStation <contato@hubstation.com.br>",
        to: ["contato@hubstation.com.br"],
        reply_to: email,
        subject: `Novo contato: ${nome}${empresa ? ` · ${empresa}` : ""}`,
        html: htmlInterno,
      }),
      enviar({
        from: "HubStation <contato@hubstation.com.br>",
        to: [email],
        subject: `Obrigado pelo contato, ${primeiroNome}! Nossa equipe retornará em breve.`,
        html: htmlAgradecimento,
      }),
    ]);

    if (!notifResp.ok) {
      console.error("Resend erro interno:", await notifResp.text());
      return NextResponse.json({ error: "Falha no envio" }, { status: 502 });
    }
    if (!confirmResp.ok) {
      // O contato chegou pra equipe; o agradecimento é secundário.
      console.warn("Agradecimento não enviado:", await confirmResp.text());
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("Erro de rede ao falar com o Resend:", err);
    return NextResponse.json({ error: "Erro de rede" }, { status: 502 });
  }
}

export async function GET() {
  return NextResponse.json({ error: "Método não permitido" }, { status: 405 });
}
