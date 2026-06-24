import { redirect } from "next/navigation";

// Pagina antiga consolidada em /sindicompany/assets. Redirect mantem
// bookmarks/links externos funcionando.
export default function PatternsPage() {
  redirect("/sindicompany/assets");
}
