"use server";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { supabaseConfig } from "@/lib/config";
import type { FormState } from "@/lib/clientes";

export async function login(_: FormState, form: FormData): Promise<FormState> {
  if (!supabaseConfig()) return { error: "O acesso ainda está em preparação." };
  const email = String(form.get("email") ?? "").trim();
  const password = String(form.get("password") ?? "");
  if (!email || !password || email.length > 254 || password.length > 1024)
    return { error: "Informe seu e-mail e sua senha." };
  const supabase = await createClient();
  try {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error)
      return {
        error: "Não foi possível entrar. Confira os dados e tente novamente.",
      };
  } catch {
    return {
      error:
        "O serviço de acesso está indisponível. Tente novamente em instantes.",
    };
  }
  redirect("/clientes");
}

export async function logout() {
  if (supabaseConfig()) {
    const supabase = await createClient();
    const { error } = await supabase.auth.signOut();
    if (error)
      throw new Error("Não foi possível encerrar a sessão. Tente novamente.");
  }
  redirect("/login");
}
