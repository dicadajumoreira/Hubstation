import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/sindicompany/auth";
import { AssetExplorer } from "../../asset-explorer";
import { createLeafUploadIntent } from "../../asset-upload-action";

export default async function ByAssetsPage({
  params,
}: {
  params: Promise<{ path?: string[] }>;
}) {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!verifySessionToken(token)) {
    redirect("/sindicompany/login");
  }

  const { path = [] } = await params;
  return (
    <AssetExplorer
      brand="bysindicompany"
      path={path}
      uploadIntent={createLeafUploadIntent}
    />
  );
}
