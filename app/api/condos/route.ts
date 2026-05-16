import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { slugify } from "@/lib/utils";
import { isReservedSlug } from "@/lib/tenant";

const SLUG_RE = /^[a-z0-9-]{2,40}$/;

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Não autenticado" }, { status: 401 });
  }

  const body = await request.json().catch(() => null);
  if (!body?.name || typeof body.name !== "string") {
    return NextResponse.json({ error: "Nome obrigatório" }, { status: 400 });
  }

  const name = body.name.trim();
  const rawSlug = (body.slug ?? slugify(name)).toString().toLowerCase();
  if (!SLUG_RE.test(rawSlug)) {
    return NextResponse.json(
      { error: "Subdomínio inválido (use a-z, 0-9, hífen)" },
      { status: 400 },
    );
  }
  if (isReservedSlug(rawSlug)) {
    return NextResponse.json(
      { error: "Subdomínio reservado, escolha outro" },
      { status: 400 },
    );
  }

  // Use admin client to insert + create membership atomically (RLS would
  // require the membership row before the user can read the condo).
  const admin = createAdminClient();

  const { data: existing } = await admin
    .from("condos")
    .select("id")
    .eq("slug", rawSlug)
    .maybeSingle();
  if (existing) {
    return NextResponse.json(
      { error: "Subdomínio já em uso" },
      { status: 409 },
    );
  }

  const { data: condo, error: insertError } = await admin
    .from("condos")
    .insert({ slug: rawSlug, name, created_by: user.id })
    .select("id, slug, name")
    .single();

  if (insertError || !condo) {
    return NextResponse.json(
      { error: insertError?.message ?? "Erro ao criar" },
      { status: 500 },
    );
  }

  const { error: membershipError } = await admin.from("memberships").insert({
    condo_id: condo.id,
    user_id: user.id,
    role: "sindico",
  });
  if (membershipError) {
    return NextResponse.json(
      { error: membershipError.message },
      { status: 500 },
    );
  }

  // TODO (Fase 2): provisionar subdomínio no Netlify via API.
  // POST https://api.netlify.com/api/v1/sites/{site_id}/domain_aliases

  return NextResponse.json({ condo });
}
