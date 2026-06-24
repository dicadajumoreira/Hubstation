"use client";

/**
 * Editor de texto enxuto pra o CORPO do comunicado.
 *
 * Apoiado no TipTap (StarterKit + Underline). UX deliberadamente simples
 * pra qualquer editora: 3 botoes (B / I / U), atalhos de teclado padrao
 * (Ctrl/Cmd+B, +I, +U) e um <input type=hidden> com o HTML pra o form
 * server-side ler.
 *
 * O HTML que sai aqui e' propositadamente limitado: so paragrafos,
 * quebras (<br>) e os 3 inlines (<strong>, <em>, <u>). A sanitizacao
 * no servidor (lib/sindicompany/comunicados.ts) garante isso por
 * regex caso algo escape.
 */

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import { useEffect, useState } from "react";

interface Props {
  name: string;
  defaultValue?: string;
  placeholder?: string;
  required?: boolean;
  /** Altura minima do campo, em px. Default 200. */
  minHeight?: number;
}

export function RichTextEditor({
  name,
  defaultValue = "",
  placeholder = "Digite o texto do comunicado…",
  required,
  minHeight = 200,
}: Props) {
  // Conteudo inicial: aceita HTML simples (com tags <p>, <strong>, <em>,
  // <u>, <br>) OU texto plano (quebra de linha vira <br>). Detecta pela
  // presenca de qualquer tag HTML.
  const initialContent = (() => {
    const v = defaultValue ?? "";
    if (/<\w+/.test(v)) return v;
    // texto plano -> envolve em <p> preservando quebras
    const escaped = v
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return escaped
      ? `<p>${escaped.replace(/\n/g, "<br>")}</p>`
      : "<p></p>";
  })();

  const [html, setHtml] = useState(initialContent);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Desliga features que nao usamos pra manter o output enxuto e a
        // toolbar curta. So queremos paragraph + B/I; underline vem da
        // outra extensao.
        heading: false,
        bulletList: false,
        orderedList: false,
        listItem: false,
        blockquote: false,
        codeBlock: false,
        code: false,
        horizontalRule: false,
        strike: false,
      }),
      Underline,
    ],
    content: initialContent,
    immediatelyRender: false,
    editorProps: {
      attributes: {
        // Foco visual: padding generoso, fonte legivel, sem outline nativo
        class:
          "min-h-full px-3 py-2 text-sm leading-relaxed focus:outline-none whitespace-pre-wrap [&_p]:m-0 [&_p:not(:last-child)]:mb-2",
      },
    },
    onUpdate({ editor }) {
      setHtml(editor.getHTML());
    },
  });

  // Garante que o defaultValue carregue quando trocar (ex: edicao de
  // outro comunicado sem desmontar o componente)
  useEffect(() => {
    if (editor && editor.getHTML() !== initialContent) {
      editor.commands.setContent(initialContent);
      setHtml(initialContent);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [defaultValue]);

  // Pra validacao do form (required): considera vazio se o HTML so tem
  // <p></p> ou <p><br></p>
  const isEmpty = /^<p>(<br\s*\/?>)?<\/p>$/.test(html.trim());

  const btnBase =
    "h-8 w-8 inline-flex items-center justify-center rounded-md text-sm font-semibold transition-colors hover:bg-onix-100";
  const btnActive = "bg-onix-900 text-white hover:bg-onix-800";
  const btnInactive = "text-onix-800";

  return (
    <div className="rounded-lg border border-onix-200 bg-white overflow-hidden focus-within:ring-2 focus-within:ring-mint-300">
      {/* Toolbar */}
      <div className="flex items-center gap-1 border-b border-onix-100 bg-onix-50 px-2 py-1.5">
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => editor?.chain().focus().toggleBold().run()}
          disabled={!editor}
          className={`${btnBase} ${
            editor?.isActive("bold") ? btnActive : btnInactive
          } font-bold`}
          aria-label="Negrito (Ctrl+B)"
          title="Negrito (Ctrl+B)"
        >
          B
        </button>
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => editor?.chain().focus().toggleItalic().run()}
          disabled={!editor}
          className={`${btnBase} ${
            editor?.isActive("italic") ? btnActive : btnInactive
          } italic`}
          aria-label="Itálico (Ctrl+I)"
          title="Itálico (Ctrl+I)"
        >
          I
        </button>
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => editor?.chain().focus().toggleUnderline().run()}
          disabled={!editor}
          className={`${btnBase} ${
            editor?.isActive("underline") ? btnActive : btnInactive
          } underline`}
          aria-label="Sublinhado (Ctrl+U)"
          title="Sublinhado (Ctrl+U)"
        >
          U
        </button>
        <div className="ml-auto text-xs text-g60 px-2 select-none">
          Selecione o texto e clique no botão para formatar.
        </div>
      </div>

      {/* Area editavel */}
      <div style={{ minHeight }}>
        <EditorContent editor={editor} />
        {!editor && (
          <div
            className="px-3 py-2 text-sm text-g60"
            aria-hidden="true"
          >
            {placeholder}
          </div>
        )}
      </div>

      {/* Hidden input pro form ler */}
      <input type="hidden" name={name} value={html} />
      {/* Required hack: valida com required="true" via um input
          fantasma que so e' "vazio" quando o editor esta sem texto. */}
      {required && (
        <input
          type="text"
          tabIndex={-1}
          aria-hidden="true"
          required
          value={isEmpty ? "" : "ok"}
          onChange={() => {}}
          className="sr-only absolute h-0 w-0 opacity-0"
        />
      )}
    </div>
  );
}
