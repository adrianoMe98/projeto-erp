import "server-only";
import { redirect } from "next/navigation";
import { supabaseConfig } from "@/lib/config";
import { createClient } from "@/lib/supabase/server";

export async function requireAccess(staffOnly = false) {
  if (!supabaseConfig()) redirect("/");
  const supabase = await createClient();
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();
  if (authError || !user) redirect("/login");
  const { data: perfil, error } = await supabase
    .from("perfis")
    .select("*")
    .eq("id", user.id)
    .maybeSingle();
  if (error)
    throw new Error("Não foi possível consultar seu acesso. Tente novamente.");
  if (!perfil) redirect("/acesso-pendente");
  if (staffOnly && perfil.papel === "cliente") redirect("/clientes");
  return { supabase, user, perfil };
}
