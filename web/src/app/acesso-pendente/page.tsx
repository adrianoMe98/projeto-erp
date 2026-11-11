import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { supabaseConfig } from "@/lib/config";
import { logout } from "@/app/login/actions";

export const dynamic = "force-dynamic";

export default async function PendingAccess() {
  if (!supabaseConfig()) redirect("/");
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  const { data: perfil, error } = await supabase
    .from("perfis")
    .select("id")
    .eq("id", user.id)
    .maybeSingle();
  if (error) throw new Error("Não foi possível consultar o acesso.");
  if (perfil) redirect("/clientes");
  return (
    <main className="center-card">
      <span className="pill">ACESSO PENDENTE</span>
      <h1>Sua conta está criada.</h1>
      <p>Peça ao administrador que vincule seu perfil antes de continuar.</p>
      <form action={logout}>
        <button>Sair da conta</button>
      </form>
    </main>
  );
}
