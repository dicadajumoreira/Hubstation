import { cookies } from "next/headers";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { condoFromSlug, slugifyCondo } from "@/lib/sindicompany/condominios";
import {
  getCondoFotoPublicUrl,
  getCondoMeta,
  gestorTitulo,
  listCondoMetas,
  listPatternUrls,
} from "@/lib/sindicompany/condominios-db";
import { PrintButton } from "./print-button";

async function resolveCondoNome(slug: string): Promise<string | null> {
  const e = condoFromSlug(slug);
  if (e) return e;
  try {
    const metas = await listCondoMetas();
    return metas.find((x) => slugifyCondo(x.nome) === slug)?.nome ?? null;
  } catch {
    return null;
  }
}

export default async function RevistaBoasVindasPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) redirect("/sindicompany/login");

  const { slug } = await params;
  const nome = await resolveCondoNome(slug);
  if (!nome) notFound();
  const meta = await getCondoMeta(nome).catch(() => null);

  const sindicoNome = meta?.sindico_nome ?? "";
  const sindico2Nome = (meta?.sindico2_nome ?? "").trim();
  const temDupla = !!sindico2Nome;
  const g1 = meta?.sindico_genero;
  const g2 = meta?.sindico2_genero;
  // 'empresa' = sindicatura feita por administradora -> a revista fala
  // aos moradores como uma equipe (1a pessoa do plural). Quando ha
  // DUPLA de sindicos, o texto tambem vai em primeira pessoa do plural
  // ("nos") com concordancia automatica conforme os generos.
  const ehEmpresa = g1 === "empresa";
  const ehPlural = temDupla || ehEmpresa;
  // Titulo individual (so usado quando NAO ha dupla).
  const sindicoTitulo = ehEmpresa
    ? "Sindicatura Profissional"
    : g1 === "feminino"
      ? "Síndica"
      : "Síndico";
  // Titulo coletivo da dupla: F+F -> "Síndicas"; senao -> "Síndicos".
  const tituloDupla = (g1 === "feminino" && g2 === "feminino") ? "Síndicas" : "Síndicos";
  // Concordancia da carta plural (Obrigado/Obrigada). F+F -> "Obrigadas";
  // M+F ou M+M -> "Obrigados". Empresa sem dupla -> "Obrigado pela
  // confianca" (mantido).
  const obrigadosConcordancia = (g1 === "feminino" && g2 === "feminino")
    ? "Obrigadas"
    : "Obrigados";
  const sindicoFoto2 = meta?.sindico2_foto_path ? getCondoFotoPublicUrl(meta.sindico2_foto_path) : null;
  const logoUrl = meta?.logo_url ?? null;
  const logoCondominioUrl = meta?.logo_condominio_url ?? null;
  // Logo da contra-capa: prefere o do condominio; cai pro do sindico.
  const logoContracapa = logoCondominioUrl ?? logoUrl;
  const sindicoFoto = meta?.sindico_foto_path ? getCondoFotoPublicUrl(meta.sindico_foto_path) : null;
  const temGestor = !!(meta?.gestor_nome && meta.gestor_nome.trim());
  const gestorNome = temGestor ? meta!.gestor_nome! : "";
  const gestorCargo = temGestor ? gestorTitulo(meta!.gestor_genero) : "";
  const gestorFoto = temGestor && meta?.gestor_foto_path ? getCondoFotoPublicUrl(meta.gestor_foto_path) : null;
  // Visibilidade do contato do(a) sindico(a): flags granulares
  // (default true). Nome e cargo aparecem sempre.
  const mostrarWhatsSindico = meta ? meta.mostrar_whatsapp_sindico !== false : true;
  const mostrarEmailSindico = meta ? meta.mostrar_email_sindico !== false : true;
  const equipe = (meta?.equipe_atendimento ?? []).filter((m) => m.nome || m.cargo);
  const comunidadeUrl = meta?.comunidade_url ?? "";
  const qrUrl = meta?.comunidade_qrcode_path ? getCondoFotoPublicUrl(meta.comunidade_qrcode_path) : null;
  const capaUrl = meta?.boasvindas_capa_path ? getCondoFotoPublicUrl(meta.boasvindas_capa_path) : null;
  // Patterns dos Assets Sindicompany usados como fundo decorativo das paginas.
  const patterns = ((await listPatternUrls().catch(() => [])).filter(Boolean) as string[]);
  const patternFor = (i: number): string | null =>
    patterns.length ? patterns[i % patterns.length] : null;
  const patternBg = (i: number, opacity: number) => {
    const url = patternFor(i);
    if (!url) return null;
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt=""
        aria-hidden="true"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity, pointerEvents: "none" }}
      />
    );
  };

  return (
    <>
      <style>{`
        @page { size: A4; margin: 0; }
        @media print {
          html, body { width: 210mm; margin: 0 !important; padding: 0 !important; background: #fff !important; }
          .sindicompany-shell { min-height: 0 !important; }
          .no-print { display: none !important; }
          .bv-pages { padding: 0 !important; margin: 0 !important; background: #fff !important; }
          .bv-page {
            box-shadow: none !important; margin: 0 !important; display: block;
            page-break-after: always; break-after: page; break-inside: avoid;
          }
          .bv-page:last-child { page-break-after: auto; break-after: auto; }
          .bv-page, .bv-safe { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        }
        .bv-page {
          width: 210mm; height: 297mm; margin: 16px auto; background: #fff;
          box-shadow: 0 4px 24px rgba(0,0,0,.12); position: relative; overflow: hidden;
          font-family: 'Epilogue', sans-serif; color: #1A1C29;
          box-sizing: border-box;
        }
        /* Camada interna que ocupa a folha inteira (sem borda branca) e
           recorta qualquer conteudo que passe do tamanho da pagina A4. */
        .bv-safe {
          position: absolute; inset: 0; overflow: hidden;
        }
      `}</style>

      <div className="no-print sticky top-0 z-10 flex items-center justify-between bg-onix-900 text-white px-6 py-3">
        <Link href={`/sindicompany/condominios/${slug}`} className="text-sm text-white/80 hover:text-white">
          ← Voltar para o cadastro
        </Link>
        <div className="text-sm">
          Revista de Boas-Vindas · <strong>{nome}</strong>
        </div>
        <PrintButton baseName={`revista-boas-vindas-${nome}`} />
      </div>

      <div className="bv-pages bg-onix-50 py-6">
        {/* ---------- PÁGINA 1 — CAPA ---------- */}
        <div className="bv-page">
          <div className="bv-safe">
            {capaUrl ? (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={capaUrl} alt="" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />
                <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg,rgba(26,28,41,.35) 0%,rgba(26,28,41,.55) 55%,rgba(26,28,41,.92) 100%)" }} />
              </>
            ) : (
              <div style={{ position: "absolute", inset: 0, background: "linear-gradient(160deg,#84C7D3 0%,#1A1C29 100%)" }} />
            )}
            {/* Logo do sindico: topo, canto esquerdo, ate ~metade da pagina (105mm de 210mm) */}
            {logoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={logoUrl}
                alt="Logo do síndico"
                style={{ position: "absolute", top: "10mm", left: "10mm", maxWidth: "98mm", maxHeight: "62mm", objectFit: "contain", filter: "drop-shadow(0 4px 12px rgba(0,0,0,.25))" }}
              />
            ) : (
              <div style={{ position: "absolute", top: "12mm", left: "10mm", fontSize: "11pt", letterSpacing: ".3em", textTransform: "uppercase", color: "rgba(255,255,255,.85)" }}>
                {ehEmpresa ? sindicoNome : `${sindicoTitulo} ${sindicoNome}`}
              </div>
            )}
            <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "82mm 18mm 32mm", textAlign: "center", color: "#fff" }}>
              <h1 style={{ fontSize: "28pt", fontWeight: 900, lineHeight: 1.15, margin: 0 }}>
                Seja bem-vindo, Condomínio {nome}.
              </h1>
              <p style={{ fontSize: "15pt", fontWeight: 600, marginTop: "9mm", color: "#DABDA9" }}>
                Agora vocês fazem parte da nossa família.
              </p>
            </div>
            <div style={{ position: "absolute", bottom: "9mm", left: "8mm", textAlign: "left", color: "rgba(255,255,255,.7)", fontSize: "9pt", letterSpacing: ".1em" }}>
              Revista de Boas-Vindas
            </div>
          </div>
        </div>

        {/* ---------- PÁGINA 2 — CARTA + EQUIPE ---------- */}
        <div className="bv-page">
          <div className="bv-safe">
          {patternBg(0, 0.06)}
          <div style={{ position: "relative", padding: "14mm 16mm 22mm" }}>
            <div style={{ fontSize: "9pt", letterSpacing: ".26em", textTransform: "uppercase", color: "#84C7D3", fontWeight: 700, marginBottom: "4mm" }}>
              Carta de agradecimento
            </div>
            <h2 style={{ fontSize: "20pt", fontWeight: 800, margin: "0 0 6mm", lineHeight: 1.1 }}>
              {temDupla
                ? `${obrigadosConcordancia} pelo voto de confiança.`
                : ehEmpresa
                  ? "Obrigado pela confiança."
                  : g1 === "feminino"
                    ? "Obrigada pelo voto de confiança."
                    : "Obrigado pelo voto de confiança."}
            </h2>
            <div style={{ fontSize: "11.5pt", lineHeight: 1.6, color: "#3a3d4a", textAlign: "justify" }}>
              <p style={{ margin: "0 0 4mm" }}>
                {ehPlural
                  ? `Prezados moradores do Condomínio ${nome},`
                  : `Caro morador do Condomínio ${nome},`}
              </p>
              {temDupla ? (
                <p style={{ margin: "0 0 4mm" }}>
                  É com gratidão que recebemos a confiança de vocês na nossa eleição
                  como {tituloDupla.toLowerCase()}. Assumimos esse papel com
                  responsabilidade e o compromisso de cuidar do nosso lar com
                  transparência, organização e atenção a cada um de vocês.
                </p>
              ) : ehEmpresa ? (
                <p style={{ margin: "0 0 4mm" }}>
                  É com gratidão que recebemos a confiança de vocês para
                  administrar o condomínio. Assumimos esse papel com
                  responsabilidade e o compromisso de cuidar do lar de vocês com
                  transparência, organização e atenção a cada morador.
                </p>
              ) : (
                <p style={{ margin: "0 0 4mm" }}>
                  É com gratidão que recebo a confiança de vocês na minha eleição
                  como {sindicoTitulo.toLowerCase()}. Assumo esse papel com
                  responsabilidade e o compromisso de cuidar do nosso lar com
                  transparência, organização e atenção a cada um de vocês.
                </p>
              )}
              <p style={{ margin: "0 0 4mm" }}>
                A partir de agora, {ehPlural ? "contamos" : "conto"} com a sua participação para construir
                uma convivência melhor todos os dias, com transparência e cuidado
                com o nosso lar.
              </p>
              {comunidadeUrl && (
                <p style={{ margin: "0 0 4mm" }}>
                  <strong>Faça parte da comunidade de WhatsApp do condomínio.</strong>{" "}
                  É lá que circulam avisos, novidades e o dia a dia do prédio.
                  O link e o QR code estão na próxima página.
                </p>
              )}
              <p style={{ margin: "4mm 0 0", fontWeight: 700 }}>
                {temDupla
                  ? `${tituloDupla} ${sindicoNome} e ${sindico2Nome}`
                  : ehEmpresa
                    ? sindicoNome || "Sindicatura Profissional"
                    : sindicoNome
                      ? `${sindicoTitulo} ${sindicoNome}`
                      : sindicoTitulo}
              </p>
            </div>

            {/* Dados do síndico / gestor em destaque.
                Se a sindicatura e uma EMPRESA e existe gestor, a foto do
                gestor (o rosto do atendimento no dia a dia) aparece em
                destaque, antes do bloco da administradora. */}
            {(() => {
              const gestorDestaque = ehEmpresa && temGestor;
              const titulo1 = ehEmpresa
                ? "Sindicatura Profissional"
                : g1 === "feminino"
                  ? "Síndica"
                  : "Síndico";
              const titulo2 = g2 === "empresa"
                ? "Sindicatura Profissional"
                : g2 === "feminino"
                  ? "Síndica"
                  : "Síndico";
              const sindicoCard = (
                <div key="sindico" style={{ flex: gestorDestaque ? "1 1 60mm" : "1 1 70mm", minWidth: "60mm", background: "#F4F4F5", borderRadius: "4mm", padding: "6mm" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "4mm" }}>
                    {sindicoFoto && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={sindicoFoto} alt={sindicoNome} style={{ width: "16mm", height: "16mm", borderRadius: "50%", objectFit: "cover" }} />
                    )}
                    <div>
                      {/* Nome em cima, cargo embaixo */}
                      <div style={{ fontSize: "13pt", fontWeight: 800, lineHeight: 1.2 }}>{sindicoNome || "—"}</div>
                      <div style={{ fontSize: "9pt", letterSpacing: ".14em", textTransform: "uppercase", color: "#84C7D3", fontWeight: 700, marginTop: "1mm" }}>{titulo1}</div>
                    </div>
                  </div>
                  {((mostrarWhatsSindico && meta?.sindico_whatsapp) ||
                    (mostrarEmailSindico && meta?.sindico_email)) && (
                    <div style={{ marginTop: "4mm", fontSize: "10pt", color: "#3a3d4a" }}>
                      {mostrarWhatsSindico && meta?.sindico_whatsapp && (
                        <div>WhatsApp: {meta.sindico_whatsapp}</div>
                      )}
                      {mostrarEmailSindico && meta?.sindico_email && (
                        <div>E-mail: {meta.sindico_email}</div>
                      )}
                    </div>
                  )}
                  {temDupla && (
                    <div style={{ marginTop: "4mm", borderTop: "1px dashed #d4d4d8", paddingTop: "3mm" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "4mm" }}>
                        {sindicoFoto2 && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={sindicoFoto2} alt={sindico2Nome} style={{ width: "16mm", height: "16mm", borderRadius: "50%", objectFit: "cover" }} />
                        )}
                        <div>
                          <div style={{ fontSize: "13pt", fontWeight: 800, lineHeight: 1.2 }}>{sindico2Nome}</div>
                          <div style={{ fontSize: "9pt", letterSpacing: ".14em", textTransform: "uppercase", color: "#84C7D3", fontWeight: 700, marginTop: "1mm" }}>{titulo2}</div>
                        </div>
                      </div>
                      {(meta?.sindico2_whatsapp || meta?.sindico2_email) && (
                        <div style={{ marginTop: "3mm", fontSize: "10pt", color: "#3a3d4a" }}>
                          {meta?.sindico2_whatsapp && <div>WhatsApp: {meta.sindico2_whatsapp}</div>}
                          {meta?.sindico2_email && <div>E-mail: {meta.sindico2_email}</div>}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
              const gestorCard = temGestor ? (
                <div key="gestor" style={{ flex: gestorDestaque ? "1 1 100mm" : "1 1 70mm", minWidth: "60mm", background: gestorDestaque ? "#1A1C29" : "#F4F4F5", color: gestorDestaque ? "#fff" : undefined, borderRadius: "4mm", padding: "6mm" }}>
                  {gestorDestaque && (
                    <div style={{ fontSize: "8.5pt", letterSpacing: ".22em", textTransform: "uppercase", color: "#84C7D3", fontWeight: 700, marginBottom: "4mm" }}>
                      Seu contato no dia a dia
                    </div>
                  )}
                  <div style={{ display: "flex", alignItems: "center", gap: "5mm" }}>
                    {gestorFoto && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={gestorFoto} alt={gestorNome} style={{ width: gestorDestaque ? "30mm" : "16mm", height: gestorDestaque ? "30mm" : "16mm", borderRadius: "50%", objectFit: "cover", border: gestorDestaque ? "2px solid #84C7D3" : undefined, flexShrink: 0 }} />
                    )}
                    <div>
                      <div style={{ fontSize: gestorDestaque ? "16pt" : "13pt", fontWeight: 800, lineHeight: 1.2 }}>{gestorNome}</div>
                      <div style={{ fontSize: "9pt", letterSpacing: ".14em", textTransform: "uppercase", color: "#84C7D3", fontWeight: 700, marginTop: "1mm" }}>{gestorCargo}</div>
                      {(meta?.gestor_whatsapp || meta?.gestor_email) && (
                        <div style={{ marginTop: "3mm", fontSize: "10pt", color: gestorDestaque ? "rgba(255,255,255,.9)" : "#3a3d4a" }}>
                          {meta?.gestor_whatsapp && <div>WhatsApp: {meta.gestor_whatsapp}</div>}
                          {meta?.gestor_email && <div>E-mail: {meta.gestor_email}</div>}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : null;
              return (
                <div style={{ display: "flex", gap: "6mm", marginTop: "7mm", flexWrap: "wrap" }}>
                  {gestorDestaque ? [gestorCard, sindicoCard] : [sindicoCard, gestorCard]}
                </div>
              );
            })()}
          </div>
          </div>
        </div>

        {/* ---------- PÁGINA 3 — COMUNIDADE ---------- */}
        <div className="bv-page">
          <div className="bv-safe">
          <div style={{ position: "absolute", inset: 0, background: "#F4F4F5" }} />
          {patternBg(1, 0.06)}
          <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "16mm 14mm", textAlign: "center" }}>
            <div style={{ fontSize: "9pt", letterSpacing: ".28em", textTransform: "uppercase", color: "#84C7D3", fontWeight: 700, marginBottom: "4mm" }}>
              Comunidade do condomínio
            </div>
            <h2 style={{ fontSize: "22pt", fontWeight: 900, margin: "0 0 5mm", lineHeight: 1.15 }}>
              Entre na comunidade de WhatsApp do {nome}.
            </h2>
            <p style={{ fontSize: "11.5pt", color: "#3a3d4a", maxWidth: "130mm", margin: "0 0 7mm" }}>
              É o canal oficial do condomínio: avisos da gestão, novidades,
              manutenções e o dia a dia do prédio. Aponte a câmera pro QR code
              ou acesse pelo link abaixo.
            </p>
            {qrUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={qrUrl} alt="QR code da comunidade" style={{ width: "58mm", height: "58mm", objectFit: "contain", background: "#fff", padding: "4mm", borderRadius: "4mm", border: "2px solid #84C7D3" }} />
            ) : (
              <div style={{ width: "58mm", height: "58mm", display: "flex", alignItems: "center", justifyContent: "center", background: "#fff", borderRadius: "4mm", color: "#9ca3af", fontSize: "10pt" }}>
                (QR code não cadastrado)
              </div>
            )}
            {comunidadeUrl && (
              <div style={{ marginTop: "6mm", maxWidth: "150mm", textAlign: "center" }}>
                <div style={{ fontSize: "8.5pt", letterSpacing: ".2em", textTransform: "uppercase", color: "#84C7D3", fontWeight: 700, marginBottom: "2mm" }}>
                  Link da comunidade
                </div>
                <a href={comunidadeUrl} style={{ display: "inline-block", background: "#1A1C29", color: "#fff", fontWeight: 700, fontSize: "10pt", padding: "2.5mm 6mm", borderRadius: "999px", wordBreak: "break-all", textDecoration: "none" }}>
                  {comunidadeUrl}
                </a>
              </div>
            )}

            {/* Equipe de atendimento do condominio (movida pra ca, junto da comunidade) */}
            {equipe.length > 0 && (
              <div style={{ marginTop: "10mm", width: "100%" }}>
                <div style={{ fontSize: "8.5pt", letterSpacing: ".22em", textTransform: "uppercase", color: "#84C7D3", fontWeight: 700, marginBottom: "4mm" }}>
                  Equipe de atendimento do condomínio
                </div>
                <div style={{ display: "flex", gap: "5mm", flexWrap: "wrap", justifyContent: "center" }}>
                  {equipe.map((m, i) => {
                    const f = m.foto_path ? getCondoFotoPublicUrl(m.foto_path) : null;
                    return (
                      <div key={i} style={{ width: "28mm", textAlign: "center" }}>
                        {f ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={f} alt={m.nome} style={{ width: "20mm", height: "20mm", borderRadius: "50%", objectFit: "cover", margin: "0 auto 2mm" }} />
                        ) : (
                          <div style={{ width: "20mm", height: "20mm", borderRadius: "50%", background: "#E5E7EB", margin: "0 auto 2mm" }} />
                        )}
                        <div style={{ fontSize: "8.5pt", fontWeight: 700, lineHeight: 1.2 }}>{m.nome}</div>
                        <div style={{ fontSize: "7pt", color: "#6b7280", lineHeight: 1.2 }}>{m.cargo}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
          <div style={{ position: "absolute", bottom: "9mm", left: "8mm", textAlign: "left", color: "#9ca3af", fontSize: "9pt" }}>
            Sindicompany · gestão condominial
          </div>
          </div>
        </div>

        {/* ---------- PÁGINA 4 — CONTRA-CAPA ---------- */}
        <div className="bv-page">
          <div className="bv-safe">
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(200deg,#1A1C29 0%,#1A1C29 45%,#84C7D3 100%)" }} />
          {patternBg(2, 0.12)}
          <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "space-between", alignItems: "center", padding: "20mm 18mm 16mm", textAlign: "center", color: "#fff" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "9mm" }}>
              {logoContracapa ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={logoContracapa} alt="Logo" style={{ maxWidth: "104mm", maxHeight: "48mm", objectFit: "contain", filter: "drop-shadow(0 4px 12px rgba(0,0,0,.25))" }} />
              ) : (
                <div style={{ fontSize: "20pt", fontWeight: 900, letterSpacing: ".04em" }}>Condomínio {nome}</div>
              )}
              <div>
                <h2 style={{ fontSize: "24pt", fontWeight: 900, lineHeight: 1.15, margin: 0 }}>
                  Conte com a gente, Condomínio {nome}.
                </h2>
                <p style={{ fontSize: "13pt", fontWeight: 600, marginTop: "6mm", color: "#DABDA9" }}>
                  Uma gestão feita de perto, todo dia.
                </p>
              </div>
            </div>

            {(sindicoNome || temGestor) && (
              <div style={{ display: "flex", gap: "10mm", flexWrap: "wrap", justifyContent: "center" }}>
                {sindicoNome && (
                  <div style={{ minWidth: "55mm" }}>
                    <div style={{ fontSize: "12pt", fontWeight: 800 }}>{sindicoNome}</div>
                    <div style={{ fontSize: "8.5pt", letterSpacing: ".14em", textTransform: "uppercase", color: "rgba(255,255,255,.8)", marginTop: "1mm" }}>{sindicoTitulo}</div>
                    {mostrarWhatsSindico && meta?.sindico_whatsapp && (
                      <div style={{ fontSize: "9.5pt", marginTop: "2mm", color: "rgba(255,255,255,.9)" }}>WhatsApp: {meta.sindico_whatsapp}</div>
                    )}
                    {mostrarEmailSindico && meta?.sindico_email && (
                      <div style={{ fontSize: "9.5pt", color: "rgba(255,255,255,.9)" }}>E-mail: {meta.sindico_email}</div>
                    )}
                  </div>
                )}
                {temGestor && (
                  <div style={{ minWidth: "55mm" }}>
                    <div style={{ fontSize: "12pt", fontWeight: 800 }}>{gestorNome}</div>
                    <div style={{ fontSize: "8.5pt", letterSpacing: ".14em", textTransform: "uppercase", color: "rgba(255,255,255,.8)", marginTop: "1mm" }}>{gestorCargo}</div>
                    {meta?.gestor_whatsapp && (
                      <div style={{ fontSize: "9.5pt", marginTop: "2mm", color: "rgba(255,255,255,.9)" }}>WhatsApp: {meta.gestor_whatsapp}</div>
                    )}
                    {meta?.gestor_email && (
                      <div style={{ fontSize: "9.5pt", color: "rgba(255,255,255,.9)" }}>E-mail: {meta.gestor_email}</div>
                    )}
                  </div>
                )}
              </div>
            )}

            <div style={{ color: "rgba(255,255,255,.7)", fontSize: "9pt", letterSpacing: ".1em" }}>
              Sindicompany · gestão condominial profissional
            </div>
          </div>
          </div>
        </div>
      </div>
    </>
  );
}
