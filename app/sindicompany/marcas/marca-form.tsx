import type { Marca } from "@/lib/sindicompany/marcas-db";

const inputCls =
  "block w-full rounded-md border border-onix-100 bg-white px-3 py-2 text-sm text-onix-900 focus:outline-none focus:ring-2 focus:ring-mint-300";

// Cores base (tema Sindicompany) — ponto de partida pra marca nova. As
// chaves sao as MESMAS que o template do engine usa.
const PALETA_BASE: Record<string, string> = {
  onix: "#182028",
  mint: "#88c8d0",
  sand: "#e0b098",
  lavender: "#bfc0ff",
  purple: "#8890d0",
  white: "#ffffff",
  gray_5: "#faf7f2",
};

// Extrai o nome da familia de um stack CSS ("'Playfair', Georgia, serif"
// -> "Playfair") pra preencher o input na edicao.
function familyName(stack: string | undefined): string {
  if (!stack) return "";
  const m = stack.match(/^\s*'([^']+)'|^\s*"([^"]+)"|^\s*([^,]+)/);
  return (m?.[1] || m?.[2] || m?.[3] || "").trim();
}

const PALETA_CAMPOS: { key: string; label: string; papel: string }[] = [
  { key: "onix", label: "Onix / Navy", papel: "texto e fundos escuros" },
  { key: "mint", label: "Acento", papel: "destaque, confiança" },
  { key: "sand", label: "Quente", papel: "tom humano, calor" },
  { key: "lavender", label: "Lavender", papel: "inovação / tech" },
  { key: "purple", label: "Purple", papel: "profundidade / IA" },
  { key: "white", label: "Branco", papel: "branco puro" },
  { key: "gray_5", label: "Paper", papel: "fundo claro / off-white" },
];

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

/** Form de criar/editar marca. `marca` ausente = criar. Na edicao o slug
 *  e read-only (e a FK de carrosseis.brand e o prefixo dos buckets). */
export function MarcaForm({
  action,
  marca,
}: {
  action: (formData: FormData) => void | Promise<void>;
  marca?: Marca;
}) {
  const isEdit = !!marca;
  return (
    <form action={action} className="space-y-6">
      {isEdit && <input type="hidden" name="slug" value={marca.slug} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Nome" hint="Como a marca aparece no painel.">
          <input
            type="text"
            name="nome"
            defaultValue={marca?.nome ?? ""}
            required
            maxLength={80}
            placeholder="Ex: Consvicta"
            className={inputCls}
          />
        </Field>
        <Field label="Handle" hint="O @ do Instagram.">
          <input
            type="text"
            name="handle"
            defaultValue={marca?.handle ?? ""}
            required
            maxLength={60}
            placeholder="Ex: @consvictabr"
            className={inputCls}
          />
        </Field>
      </div>

      {isEdit ? (
        <Field label="Slug" hint="Identificador estável — não pode mudar (é a referência dos carrosséis e dos buckets).">
          <input
            type="text"
            defaultValue={marca.slug}
            disabled
            className={`${inputCls} bg-onix-50 text-g60`}
          />
        </Field>
      ) : (
        <Field
          label="Slug"
          hint="Identificador único (minúsculas, sem espaço). Ex: minhamarca. É permanente."
        >
          <input
            type="text"
            name="slug"
            required
            maxLength={40}
            placeholder="minhamarca"
            className={inputCls}
          />
        </Field>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Nicho" hint="Livre. Ex: condominial, fitness, jurídico.">
          <input
            type="text"
            name="nicho"
            defaultValue={marca?.nicho ?? ""}
            maxLength={60}
            placeholder="condominial"
            className={inputCls}
          />
        </Field>
        <Field label="Assinatura" hint="Frase de fechamento da legenda.">
          <input
            type="text"
            name="assinatura"
            defaultValue={marca?.assinatura ?? ""}
            maxLength={120}
            placeholder="Ex: Por mais lares."
            className={inputCls}
          />
        </Field>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Field
          label="Prefixo dos buckets"
          hint={isEdit ? "Prefixo dos assets no storage." : "Vazio = __<slug>-"}
        >
          <input
            type="text"
            name="bucket_prefix"
            defaultValue={marca?.bucketPrefix ?? ""}
            maxLength={40}
            placeholder="__minhamarca-"
            className={inputCls}
          />
        </Field>
        <Field label="Rota dos assets" hint={isEdit ? undefined : "Vazio = <slug>-assets"}>
          <input
            type="text"
            name="route_slug"
            defaultValue={marca?.routeSlug ?? ""}
            maxLength={60}
            placeholder="minhamarca-assets"
            className={inputCls}
          />
        </Field>
        <Field label="Ordem" hint="Posição no seletor.">
          <input
            type="number"
            name="ordem"
            defaultValue={marca?.ordem ?? 0}
            className={inputCls}
          />
        </Field>
      </div>

      <Field
        label="Persona (guia de copy)"
        hint="O system prompt da marca: voz, público, tom, o que viraliza, o que nunca fazer. É o que dirige o copy gerado."
      >
        <textarea
          name="persona"
          defaultValue={marca?.persona ?? ""}
          rows={16}
          placeholder="Você é especialista em criar carrosséis para o Instagram da ..."
          className={`${inputCls} font-mono text-xs leading-relaxed`}
        />
      </Field>

      <Field
        label="Temas sugeridos"
        hint="Um tema por linha. Aparecem no seletor de tema do /carrossel/novo."
      >
        <textarea
          name="temas"
          defaultValue={(marca?.temasSugeridos ?? []).join("\n")}
          rows={8}
          placeholder={"Direitos do morador\nInadimplência\nOutro"}
          className={`${inputCls} text-xs`}
        />
      </Field>

      <div className="space-y-2">
        <div>
          <label className="block text-sm font-medium text-onix-900">
            Paleta da marca
          </label>
          <p className="text-xs text-g60">
            Cores usadas no visual dos slides. Marca nova começa com o tema
            base — ajuste pra dar identidade própria.
          </p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 rounded-lg border border-onix-100 bg-white p-4">
          {PALETA_CAMPOS.map((c) => (
            <div key={c.key} className="space-y-1">
              <div className="text-xs font-medium text-onix-900">{c.label}</div>
              <div className="text-[11px] text-g60 leading-tight">{c.papel}</div>
              <input
                type="color"
                name={`paleta_${c.key}`}
                defaultValue={marca?.paleta?.[c.key] ?? PALETA_BASE[c.key]}
                className="h-9 w-full cursor-pointer rounded-md border border-onix-100 bg-white p-0.5"
              />
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-onix-900">
            Tipografia (fontes da marca)
          </label>
          <p className="text-xs text-g60">
            Envie um <strong>.zip</strong> com os arquivos <code>.otf</code>/
            <code>.ttf</code>/<code>.woff</code>/<code>.woff2</code> da marca e
            diga qual família é o título, o corpo e os números. Os nomes dos
            arquivos devem começar com o nome da família e indicar o peso/estilo
            (ex: <code>Playfair-Bold.woff2</code>, <code>Inter-Regular.woff2</code>).
            As 3 marcas internas já têm fontes próprias — isto vale para marcas novas.
          </p>
        </div>
        {marca?.tipografia?.faces?.length ? (
          <p className="text-xs text-mint-700">
            {marca.tipografia.faces.length} arquivo(s) de fonte já importado(s).
            Envie um novo zip só se quiser substituir.
          </p>
        ) : null}
        <input
          type="file"
          name="fontes_zip"
          accept=".zip,application/zip,application/x-zip-compressed"
          className="block w-full text-sm text-onix-900 file:mr-3 file:rounded-md file:border-0 file:bg-onix-900 file:px-3 file:py-2 file:text-white file:text-sm"
        />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Field label="Fonte de título" hint="Família dos títulos/destaques.">
            <input
              type="text"
              name="fonte_display"
              defaultValue={familyName(marca?.tipografia?.display)}
              maxLength={60}
              placeholder="Ex: Playfair Display"
              className={inputCls}
            />
          </Field>
          <Field label="Fonte de corpo" hint="Família do texto corrido.">
            <input
              type="text"
              name="fonte_body"
              defaultValue={familyName(marca?.tipografia?.body)}
              maxLength={60}
              placeholder="Ex: Inter"
              className={inputCls}
            />
          </Field>
          <Field label="Fonte de números" hint="Opcional. Vazio = usa a de corpo.">
            <input
              type="text"
              name="fonte_numeric"
              defaultValue={familyName(marca?.tipografia?.numeric)}
              maxLength={60}
              placeholder="Ex: Oswald"
              className={inputCls}
            />
          </Field>
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-onix-900">
        <input
          type="checkbox"
          name="ativo"
          defaultChecked={marca ? marca.ativo : true}
          className="rounded border-onix-200"
        />
        Marca ativa (aparece no seletor de carrossel)
      </label>

      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          className="inline-flex items-center px-4 py-2.5 rounded-lg bg-onix-900 text-white font-medium hover:bg-onix-800 text-sm"
        >
          {isEdit ? "Salvar alterações" : "Criar marca"}
        </button>
        <a
          href="/sindicompany/marcas"
          className="text-sm text-g60 hover:text-onix-900"
        >
          Cancelar
        </a>
      </div>
    </form>
  );
}
