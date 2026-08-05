# Hubstation

Plataforma multi-tenant de dashboards para condomínios.

- **Domínio raiz:** `sindico.info`
- **Painel central:** `sindico.info/admin`
- **Dashboard por condomínio:** `<slug>.sindico.info`
- **Site institucional da HubStation:** `hubstation.com.br`

Cada síndico pode gerenciar múltiplos condomínios. Cada condomínio tem dados
isolados (RLS no Postgres) e três perfis de acesso: `sindico`, `conselheiro`,
`morador`.

---

## Stack

- Next.js 15 (App Router) + React 19 + TypeScript
- Tailwind CSS
- Supabase (Postgres + Auth + Storage)
- Deploy: Netlify (`@netlify/plugin-nextjs`)

---

## Setup local

### 1. Instalar dependências

```bash
npm install
```

### 2. Criar `.env.local`

Copie `.env.example` para `.env.local` e preencha:

```bash
cp .env.example .env.local
```

Pegue os valores no painel do Supabase (Settings → API):

- `NEXT_PUBLIC_SUPABASE_URL` (Project URL)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (anon public)
- `SUPABASE_SERVICE_ROLE_KEY` (service_role — **secreta**)

### 3. Rodar o schema no Supabase

No painel do Supabase: **SQL Editor → New query → cole o conteúdo de
`supabase/schema.sql` → RUN**.

Cria as tabelas, RLS policies, triggers.

### 4. Iniciar o dev server

```bash
npm run dev
```

Abre em `http://localhost:3000`.

> Para testar subdomínios localmente, use uma URL tipo
> `http://clubparkbutanta.localhost:3000` (alguns navegadores resolvem
> automaticamente; senão, edite `/etc/hosts`).

---

## Deploy (Netlify)

1. Conecte o repositório `dicadajumoreira/Hubstation` na Netlify.
2. Em **Site configuration → Environment variables**, adicione todas as
   vars do `.env.example` com os valores reais.
3. Em **Domain management**, adicione `www.sindico.info` (já está) e
   subdomínios conforme cria cada condomínio.
4. Build automático no push para `main`.

### Site institucional da HubStation (`hubstation.com.br`)

O site é **estático**, servido por este mesmo deploy. As páginas vivem em
`public/hubstation/` e o `middleware.ts` reescreve por host:

| URL pública | Arquivo |
|---|---|
| `hubstation.com.br/` | `public/hubstation/index.html` |
| `hubstation.com.br/sobre` | `public/hubstation/sobre.html` |
| `hubstation.com.br/servicos` | `public/hubstation/servicos.html` |
| `hubstation.com.br/eventos` | `public/hubstation/eventos.html` |
| `hubstation.com.br/blog` | `public/hubstation/blog.html` |
| `hubstation.com.br/contato` | `public/hubstation/contato.html` |
| `hubstation.com.br/sitemap.xml` | `public/hubstation/sitemap.xml` |
| `hubstation.com.br/robots.txt` | `public/hubstation/robots.txt` |

CSS, JS e imagens são pedidos direto pelos caminhos absolutos
`/hubstation/css/…`, `/hubstation/js/…`, `/hubstation/assets/…` — por isso as
regras de cache no `netlify.toml` miram esses paths, e não a URL limpa.

As URLs antigas com `.html` (`/sobre.html`) respondem **301** para a versão
limpa, preservando o que o Google já indexou.

**Editar o site:** é HTML e CSS puro, sem build. Mexeu em
`public/hubstation/*.html` ou `css/style.css`, commitou, subiu.

**Testar local:** `npm run dev` e abra `http://hubstation.localhost:3000`
(o resolvedor de host reconhece esse alias).

**Formulário de contato:** `POST /api/contato` (`app/api/contato/route.ts`)
dispara dois e-mails via Resend — notificação para `contato@hubstation.com.br`
e agradecimento para quem preencheu. Precisa de `RESEND_API_KEY` nas env vars
da Netlify e do domínio `hubstation.com.br` verificado no painel do Resend.

**Para apontar o domínio:** adicione `hubstation.com.br` e
`www.hubstation.com.br` em *Domain management* deste site na Netlify, e
desative o site antigo (`633ef4c2-2b7c-4e93-b67c-070a1b650ff6`) só depois de
confirmar que o novo está respondendo.

### Subdomínio por condomínio

A criação de subdomínio será automatizada na Fase 2 via Netlify API
(`POST /sites/{site_id}/domain_aliases`). Por enquanto, ao criar um novo
condomínio, adicione manualmente o alias no painel da Netlify.

---

## Estrutura

```
app/
├── page.tsx                    ← landing
├── admin/                      ← painel central (sindico.info/admin)
│   ├── login/
│   ├── signup/
│   └── condos/
│       ├── page.tsx            ← "meus condomínios"
│       └── new/                ← criar novo
├── condo/[slug]/               ← dashboard tenant (<slug>.sindico.info)
│   ├── layout.tsx              ← shell + nav 8 abas
│   ├── page.tsx                ← Visão Geral
│   ├── financeiro/
│   ├── engenharia/
│   ├── gestao/
│   ├── juridico/
│   ├── plano/
│   ├── valpatrimonial/
│   └── documentos/
└── api/
    ├── condos/route.ts         ← POST cria condo + membership
    └── contato/route.ts        ← formulário do site da HubStation (Resend)

public/
└── hubstation/                 ← site institucional (hubstation.com.br)
    ├── *.html                  ← 6 páginas estáticas
    ├── css/style.css
    ├── js/main.js
    ├── assets/                 ← logos + og-cover.png
    ├── sitemap.xml
    └── robots.txt

lib/
├── tenant.ts                   ← resolve slug do host
├── utils.ts
└── supabase/
    ├── client.ts               ← browser
    ├── server.ts               ← server components / route handlers
    └── admin.ts                ← service_role (server-only)

middleware.ts                   ← roteia por host: <slug>.sindico.info → /condo/<slug>,
                                  hubstation.com.br → public/hubstation/
supabase/schema.sql             ← tabelas + RLS
```

---

## Roadmap

- **Fase 1 (atual):** fundação, auth, criar condomínio, shell das 8 abas.
- **Fase 2:** provisionar subdomínio na Netlify automaticamente, gestão de
  membros, branding por condomínio.
- **Fase 3:** migrar uma aba por vez do single-file original do Club Park
  Butantã (Visão Geral → Financeiro → Engenharia → Gestão → Jurídico →
  Plano Diretor → Valorização Patrimonial → Documentos).
- **Fase 4:** importador de dados do `clubparkbutanta.sindico.info`
  (localStorage + Netlify Blobs → Supabase).
