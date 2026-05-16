import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { DashboardShell } from "../../shell";
import { iniciarCarrosselAction } from "../actions";
import { BrandTemaPicker } from "./brand-tema-picker";

// Temas pro @sindicompanybr — pauta voltada pro MORADOR comum.
const TEMAS = [
  "Direitos do morador",
  "Deveres do morador",
  "Taxa de condomínio",
  "Inadimplência",
  "Prestação de contas",
  "Fundo de reserva",
  "Síndico profissional",
  "Rotina do síndico",
  "Gestão condominial",
  "Bastidores da sindicatura",
  "Conflitos entre vizinhos",
  "Barulho em condomínio",
  "Problemas com garagem",
  "Uso das áreas comuns",
  "Segurança",
  "Portaria e controle de acesso",
  "Tecnologia no condomínio",
  "Inteligência artificial em condomínios",
  "Assembleias e votações",
  "Comunicação em condomínio",
  "Grupo de WhatsApp do condomínio",
  "Animais de estimação",
  "Obras e reformas",
  "Mudanças no condomínio",
  "Funcionários do condomínio",
  "Zeladoria",
  "Limpeza e conservação",
  "Manutenção preventiva",
  "Elevadores",
  "Vazamentos",
  "Piscinas",
  "Academia do condomínio",
  "Playground",
  "Salão de festas",
  "Churrasqueira",
  "Sustentabilidade",
  "Economia no condomínio",
  "Redução de custos",
  "Energia solar",
  "Carregadores para carros elétricos",
  "Mercado livre de energia",
  "Valorização do imóvel",
  "Condomínios de luxo",
  "Condomínios clube",
  "Condomínios populares",
  "Tendências em alta",
  "Curiosidades sobre condomínios",
  "Leis e regras condominiais",
  "Código civil em condomínios",
  "Multas em condomínio",
  "Advertências",
  "LGPD em condomínios",
  "Câmeras e privacidade",
  "Convivência em condomínio",
  "Crianças em áreas comuns",
  "Idosos no condomínio",
  "Inclusão e acessibilidade",
  "Hospitalidade em condomínios",
  "Experiência do morador",
  "Administração financeira",
  "Auditoria condominial",
  "Fraudes em condomínios",
  "Compliance",
  "Compras e fornecedores",
  "Gestão de crise",
  "Assembleias polêmicas",
  "Reclamações de moradores",
  "Reclame Aqui do condomínio",
  "Síndico emocionalmente sobrecarregado",
  "Saúde mental do síndico",
  "Liderança",
  "Comunicação não violenta",
  "Mediação de conflitos",
  "Condomínio pet friendly",
  "Regras de locação por temporada",
  "Airbnb em condomínios",
  "Segurança infantil",
  "Violência doméstica em condomínios",
  "Incêndio e evacuação",
  "AVCB e documentação",
  "Seguro condominial",
  "Responsabilidade civil do síndico",
  "Vida real da portaria",
  "Curiosidades de assembleia",
  "Histórias reais de condomínio",
  "Erros que acabam com a convivência",
  "Hábitos que valorizam o condomínio",
  "O futuro da vida em condomínio",
  "Perfil dos moradores modernos",
  "Gestão humanizada",
  "Condomínio inteligente",
  "Automatização predial",
  "Biometria e reconhecimento facial",
  "Entregas e delivery",
  "Lavanderias compartilhadas",
  "Coworking em condomínio",
  "Market place interno",
  "Mini mercados em condomínio",
  "Violação de regras",
  "Cultura da reclamação",
  "Moradores difíceis",
  "Moradores antissociais",
  "O papel do conselho",
  "Administradora de condomínio",
  "Relação entre síndico e administradora",
  "Como evitar processos",
  "Condomínio endividado",
  "Planejamento orçamentário",
  "Previsão orçamentária",
  "Como reduzir conflitos",
  "Erros comuns de síndicos",
  "O que um bom síndico faz diferente",
  "Coisas que o morador deveria saber",
  "Verdades sobre morar em condomínio",
  "Etiqueta condominial",
  "Boas práticas de convivência",
  "Tendências de arquitetura condominial",
  "Hotelaria aplicada a condomínios",
  "Segurança patrimonial",
  "Gestão operacional",
  "Engenharia condominial",
  "Obras milionárias em condomínio",
  "Emergências em condomínio",
  "Gestão de fornecedores",
  "Comunicação de crise",
  "Marketing para síndicos",
  "Carreira de síndico profissional",
  "Mulheres na sindicatura",
  "Síndicos influencers",
  "Condomínio e redes sociais",
  "Moradores tóxicos",
  "Cultura organizacional em condomínios",
  "Gestão estratégica",
  "Planejamento anual do condomínio",
  "Como aumentar o engajamento dos moradores",
  "O que desvaloriza um condomínio",
  "O que faz um condomínio funcionar bem",
  "Gestão profissional vs improviso",
  "Condomínios que parecem empresa",
  "O caos silencioso dos condomínios",
  "Tendências do mercado condominial",
  "O luxo invisível da boa gestão",
  "Outro",
];

// Temas pro @bysindicompany — pauta voltada pro SÍNDICO PROFISSIONAL.
const TEMAS_BY = [
  "Liderança na sindicatura",
  "Crescimento profissional",
  "Posicionamento de mercado",
  "Autoridade profissional",
  "Gestão estratégica",
  "Inteligência emocional",
  "Bastidores da sindicatura",
  "Comunicação do síndico",
  "Assembleias difíceis",
  "Gestão de conflitos",
  "Síndico profissional moderno",
  "Síndico empreendedor",
  "Marca pessoal do síndico",
  "Networking",
  "Expansão de carteira",
  "Gestão de equipes",
  "Relação com moradores",
  "Gestão de crise",
  "Alta performance",
  "Rotina do síndico",
  "Organização operacional",
  "Produtividade",
  "Burnout do síndico",
  "Saúde mental do síndico",
  "Condomínio de alto conflito",
  "Gestão empresarial",
  "Erros comuns de síndicos",
  "Síndico iniciante",
  "Síndico em crescimento",
  "Estratégia para síndicos",
  "Reputação profissional",
  "Marketing para síndicos",
  "Instagram para síndicos",
  "Conteúdo para síndicos",
  "Carreira na sindicatura",
  "Evolução da sindicatura",
  "Futuro da gestão condominial",
  "Tendências do mercado",
  "Gestão humanizada",
  "Liderança em assembleias",
  "Postura profissional",
  "Tomada de decisão",
  "Negociação",
  "Gestão financeira",
  "Planejamento estratégico",
  "Cultura condominial",
  "Comunicação em crise",
  "Segurança jurídica na gestão",
  "Compliance condominial",
  "Gestão técnica",
  "Síndico e tecnologia",
  "IA em condomínios",
  "Automação condominial",
  "Gestão de manutenção",
  "Engenharia condominial",
  "Gestão de fornecedores",
  "Atendimento ao morador",
  "Convivência em condomínios",
  "Política em condomínios",
  "Conselho consultivo",
  "Conselho fiscal",
  "Relação com administradoras",
  "Captar condomínios",
  "Conquistar autoridade",
  "Cobrar valorização profissional",
  "Crescer no mercado",
  "Sair da sobrecarga",
  "Parar de apagar incêndios",
  "Estruturar a operação",
  "Liderar condomínios grandes",
  "Lidar com pressão",
  "Enfrentar críticas",
  "Ser respeitado pelo condomínio",
  "Conduzir reuniões",
  "Fortalecer a imagem profissional",
  "Construir credibilidade",
  "Gerar confiança",
  "Diferenciar no mercado",
  "Precificar a sindicatura",
  "Criar processos",
  "Delegar tarefas",
  "Evitar desgaste emocional",
  "Profissionalizar a gestão",
  "Presença digital",
  "Aumentar ticket médio",
  "Escalar a sindicatura",
  "Construir marca forte",
  "Crescer com apoio de rede",
  "Desenvolvimento profissional contínuo",
  "Mentalidade de crescimento",
  "Gestão por processos",
  "Síndico vs improviso",
  "Condomínio não é grupo de WhatsApp",
  "O peso da responsabilidade",
  "O lado invisível da sindicatura",
  "O síndico que ninguém vê",
  "O custo do despreparo",
  "O erro de querer agradar todos",
  "O síndico que trabalha sozinho",
  "O síndico que virou referência",
  "Perder o controle da gestão",
  "Saber liderar pessoas",
  "Quando o condomínio percebe a má gestão",
  "O mercado mudou para os síndicos",
  "O novo perfil do síndico",
  "Outros",
];

// Temas pro @consvictabr — Gestão Condominial Boutique (SP & RJ, desde 2019).
// Reflete os pilares do brand book: boutique vs plataforma, balancete
// personalizado, plano de contas customizado, prédio tratado como único,
// 20+ anos de experiência, decisão informada.
const TEMAS_CONSVICTA = [
  "Gestão Boutique vs. plataforma de gestão",
  "Balancete personalizado — por que importa",
  "Plano de contas customizado por prédio",
  "Cada condomínio tem seu jeito de funcionar",
  "Bastidores da administração boutique",
  "Decisões difíceis do dia a dia do síndico",
  "Saúde financeira do condomínio",
  "Reputação do prédio e valor do imóvel",
  "Conselho consultivo: o que importa",
  "Conformidade e legislação",
  "Sustentabilidade na gestão",
  "Tecnologia que serve a gestão (não substitui)",
  "Atendimento humano em prédios de alto padrão",
  "Mercado imobiliário vertical SP & RJ",
  "20 anos de mercado condominial",
  "Outros",
];

const FORMATOS = [
  { id: "historia_real", label: "História real", hint: "O que mais engaja e salva" },
  { id: "lista", label: "Lista", hint: "5–7 itens numerados" },
  { id: "mito_verdade", label: "Mito vs. Verdade", hint: "Compara crenças com fatos" },
  { id: "antes_depois", label: "Antes / Depois", hint: "Mostra transformação" },
  { id: "dado_choca", label: "Dado que choca", hint: "Estatística com peso" },
  { id: "tutorial", label: "Tutorial rápido", hint: "Passo a passo prático" },
  { id: "opiniao", label: "Opinião forte", hint: "Posição com argumento" },
];

const inputCls =
  "block w-full rounded-md border border-onix-100 bg-white px-3 py-2 text-sm text-onix-900 focus:outline-none focus:ring-2 focus:ring-mint-300";

export default async function NovoCarrosselPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  const params = await searchParams;
  const error = typeof params.error === "string" ? params.error : "";
  const v = (k: string): string => {
    const val = params[k];
    return Array.isArray(val) ? val[0] ?? "" : val ?? "";
  };

  return (
    <DashboardShell>
      <main className="max-w-3xl mx-auto px-6 py-12">
        <Link
          href="/sindicompany/carrossel"
          className="text-sm text-g60 hover:text-onix-900 mb-6 inline-block"
        >
          ← Voltar
        </Link>

        <header className="mb-8">
          <Stepper step={1} />
          <div className="text-xs uppercase tracking-[0.24em] text-mint-700 font-semibold mb-2 mt-6">
            Etapa 1 · Briefing
          </div>
          <h1 className="text-3xl font-bold text-onix-900">
            Comece pelo briefing
          </h1>
          <p className="text-sm text-g60 mt-2 max-w-xl">
            Conte tema, formato e quantidade de slides. A IA vai gerar 3 opções
            de copy pra você escolher na próxima etapa.
          </p>
        </header>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 mb-6">
            {error}
          </div>
        )}

        <form action={iniciarCarrosselAction} className="space-y-6">
          <BrandTemaPicker
            temasSindico={TEMAS}
            temasBy={TEMAS_BY}
            temasConsvicta={TEMAS_CONSVICTA}
            defaultBrand={v("brand") || "sindicompanybr"}
            defaultObjetivo={v("objetivo")}
            defaultTema={v("tema")}
            defaultTemaOutro={v("tema_outro")}
          />

          <Field
            label="Título interno"
            hint="Pra organização — não aparece no post."
          >
            <input
              type="text"
              name="titulo"
              defaultValue={v("titulo")}
              required
              maxLength={120}
              placeholder='Ex: "História real — síndico que reduziu inadimplência"'
              className={inputCls}
            />
          </Field>

          <Field label="Formato" hint="Como o conteúdo é apresentado.">
            <div className="grid grid-cols-2 gap-2">
              {FORMATOS.map((f) => (
                <label
                  key={f.id}
                  className="flex items-start gap-2 rounded-md border border-onix-100 bg-white px-3 py-2 cursor-pointer hover:bg-onix-50"
                >
                  <input
                    type="radio"
                    name="formato"
                    value={f.id}
                    defaultChecked={v("formato") === f.id}
                    required
                    className="mt-1"
                  />
                  <div>
                    <div className="text-sm font-medium text-onix-900">{f.label}</div>
                    <div className="text-xs text-g60">{f.hint}</div>
                  </div>
                </label>
              ))}
            </div>
          </Field>

          <Field
            label="Quantidade de slides"
            hint="De 1 a 10. Recomendado: 5 a 7."
          >
            <select
              name="n_slides"
              defaultValue={v("n_slides") || "6"}
              className={inputCls}
            >
              {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  {n} slide{n > 1 ? "s" : ""}
                </option>
              ))}
            </select>
          </Field>

          <div className="flex gap-3 pt-4 items-center">
            <button
              type="submit"
              className="rounded-lg bg-onix-900 text-white px-5 py-2.5 font-medium hover:bg-onix-800"
            >
              Seguir →
            </button>
            <span className="text-xs text-g60">
              A IA vai gerar 3 opções de copy. Pode levar 10-15 segundos.
            </span>
          </div>
        </form>
      </main>
    </DashboardShell>
  );
}

function Stepper({ step }: { step: 1 | 2 | 3 }) {
  const items = [
    { n: 1, label: "Briefing" },
    { n: 2, label: "Escolher copy" },
    { n: 3, label: "Foto da capa" },
  ];
  return (
    <nav className="flex items-center gap-2 text-xs">
      {items.map((it, i) => {
        const active = it.n === step;
        const done = it.n < step;
        return (
          <div key={it.n} className="flex items-center gap-2">
            <span
              className={`w-6 h-6 inline-flex items-center justify-center rounded-full font-semibold ${
                active
                  ? "bg-onix-900 text-white"
                  : done
                    ? "bg-mint-100 text-mint-700"
                    : "bg-onix-50 text-g60"
              }`}
            >
              {done ? "✓" : it.n}
            </span>
            <span className={active ? "text-onix-900 font-medium" : "text-g60"}>
              {it.label}
            </span>
            {i < items.length - 1 && <span className="text-g60">›</span>}
          </div>
        );
      })}
    </nav>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-onix-900">{label}</label>
      {hint && <p className="text-xs text-g60">{hint}</p>}
      {children}
    </div>
  );
}
