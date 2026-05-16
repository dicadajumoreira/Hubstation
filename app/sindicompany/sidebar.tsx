"use client";

import { useState } from "react";
import Link from "next/link";
import { logoutAction } from "./login/actions";

interface NavItem {
  label: string;
  href?: string;
  emoji?: string;
  children?: NavItem[];
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Revista Mensal",
    href: "/sindicompany/dashboard",
    emoji: "📕",
    children: [
      { label: "Edições", href: "/sindicompany/dashboard" },
      { label: "Editorial mensal", href: "/sindicompany/editorial" },
    ],
  },
  { label: "Revista de Boas-Vindas", href: "/sindicompany/boas-vindas", emoji: "📰" },
  { label: "Comunicados", href: "/sindicompany/comunicados", emoji: "📣" },
  {
    label: "Carrosséis",
    href: "/sindicompany/carrossel",
    emoji: "🎠",
    children: [
      { label: "@sindicompanybr", href: "/sindicompany/carrossel/novo?brand=sindicompanybr" },
      { label: "@bysindicompany", href: "/sindicompany/carrossel/novo?brand=bysindicompany" },
      { label: "@consvictabr", href: "/sindicompany/carrossel/novo?brand=consvictabr" },
    ],
  },
  { label: "Condomínios", href: "/sindicompany/condominios", emoji: "🏢",
    children: [
      { label: "Lista de condomínios", href: "/sindicompany/condominios" },
      { label: "Equipe de Atendimento", href: "/sindicompany/equipe-atendimento" },
    ],
  },
  {
    label: "Assets Sindicompany",
    emoji: "🎨",
    children: [
      { label: "Patterns", href: "/sindicompany/patterns" },
      { label: "Icons", href: "/sindicompany/icons" },
      { label: "Fundo Carrossel", href: "/sindicompany/icon-carrossel" },
      { label: "Logotipos", href: "/sindicompany/logos" },
    ],
  },
  {
    label: "Assets BySindicompany",
    emoji: "🪄",
    children: [{ label: "Patterns · Icons · Fundo · Logos", href: "/sindicompany/by-assets" }],
  },
  {
    label: "Assets Consvicta",
    emoji: "🌿",
    children: [{ label: "Patterns · Icons · Fundo · Logos", href: "/sindicompany/consvicta-assets" }],
  },
];

function renderItem(
  item: NavItem,
  onNavigate: () => void,
  depth = 0,
): React.ReactNode {
  const padding = depth === 0 ? "px-3" : "pl-10 pr-3";
  const fontSize = depth === 0 ? "text-sm font-medium" : "text-xs font-normal";
  const opacity = depth === 0 ? "text-white/85" : "text-white/65";

  const inner = (
    <span className="flex items-center gap-3">
      {item.emoji && <span className="text-base">{item.emoji}</span>}
      <span>{item.label}</span>
    </span>
  );

  return (
    <div key={item.label}>
      {item.href ? (
        <Link
          href={item.href}
          onClick={onNavigate}
          className={`flex items-center ${padding} py-2 rounded-md ${fontSize} ${opacity} hover:bg-white/10 hover:text-white transition-colors`}
        >
          {inner}
        </Link>
      ) : (
        <div
          className={`flex items-center ${padding} py-2 ${fontSize} ${opacity}`}
        >
          {inner}
        </div>
      )}
      {item.children && (
        <div className="mt-0.5 mb-1 space-y-0.5">
          {item.children.map((child) => renderItem(child, onNavigate, depth + 1))}
        </div>
      )}
    </div>
  );
}

export function SindicompanySidebar() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <>
      {/* Top bar mobile (visivel < lg). Fixed pra ficar fora do flex
          do shell e ocupar a largura toda. Main content do shell
          ganha padding-top no mobile pra compensar. */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-30 flex items-center justify-between bg-onix-900 text-white px-4 py-3 h-14">
        <Link
          href="/sindicompany/dashboard"
          className="flex items-center gap-2"
          onClick={close}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="https://raw.githubusercontent.com/dicadajumoreira/Sindicompany/main/Logotipo%20Sindicompany%201.png"
            alt="Sindicompany"
            className="h-6 w-auto"
            style={{ filter: "brightness(0) invert(1)" }}
          />
          <span className="text-[10px] uppercase tracking-[0.24em] font-semibold text-mint-400">
            Comunicação
          </span>
        </Link>
        <button
          type="button"
          aria-label={open ? "Fechar menu" : "Abrir menu"}
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center justify-center w-10 h-10 rounded-md hover:bg-white/10"
        >
          {open ? (
            <span className="text-xl leading-none">×</span>
          ) : (
            <span className="flex flex-col gap-1.5">
              <span className="block w-5 h-0.5 bg-white" />
              <span className="block w-5 h-0.5 bg-white" />
              <span className="block w-5 h-0.5 bg-white" />
            </span>
          )}
        </button>
      </div>

      {/* Backdrop mobile quando o menu esta aberto */}
      {open && (
        <button
          type="button"
          aria-label="Fechar menu"
          onClick={close}
          className="lg:hidden fixed inset-0 z-30 bg-black/50"
        />
      )}

      {/* Sidebar:
          - mobile (< lg): fixa, slide-in da esquerda quando open
          - desktop (lg+): sempre visivel, sticky no flow */}
      <aside
        className={
          "bg-onix-900 text-white px-4 py-6 flex flex-col w-60 shrink-0 " +
          "fixed top-0 left-0 z-40 h-screen transition-transform duration-200 " +
          (open ? "translate-x-0" : "-translate-x-full") +
          " lg:translate-x-0 lg:sticky lg:z-auto"
        }
      >
        <Link
          href="/sindicompany/dashboard"
          className="block mb-8"
          onClick={close}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="https://raw.githubusercontent.com/dicadajumoreira/Sindicompany/main/Logotipo%20Sindicompany%201.png"
            alt="Sindicompany"
            className="h-8 w-auto mb-3"
            style={{ filter: "brightness(0) invert(1)" }}
          />
          <span className="text-[10px] uppercase tracking-[0.24em] font-semibold text-mint-400">
            Comunicação
          </span>
        </Link>

        <nav className="flex-1 flex flex-col gap-0.5 overflow-y-auto">
          {NAV_ITEMS.map((item) => renderItem(item, close))}
        </nav>

        <form action={logoutAction} className="pt-4 border-t border-white/10">
          <button
            type="submit"
            className="text-xs text-white/55 hover:text-white underline-offset-2 hover:underline"
          >
            Sair
          </button>
        </form>
      </aside>
    </>
  );
}
