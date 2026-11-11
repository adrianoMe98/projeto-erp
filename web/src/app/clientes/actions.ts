"use server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireAccess } from "@/lib/auth";
import { parseCliente, type FormState } from "@/lib/clientes";

export async function saveCliente(
  id: string | null,
  _: FormState,
  form: FormData,
): Promise<FormState> {
  const { supabase } = await requireAccess(true);
  let input;
  try {
    input = parseCliente(form);
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Confira os campos.",
    };
  }
  if (id && !/^[0-9a-f-]{36}$/i.test(id))
    return { error: "Cadastro inválido." };
  const result = id
    ? await supabase
        .from("clientes")
        .update(input)
        .eq("id", id)
        .select("id")
        .maybeSingle()
    : await supabase.from("clientes").insert(input).select("id").single();
  if (result.error)
    return {
      error:
        result.error.code === "23505"
          ? "Já existe um cliente com este CNPJ."
          : "Não foi possível salvar. Confira os dados e seu acesso.",
    };
  if (!result.data)
    return {
      error: "Cadastro não encontrado ou sem permissão para alteração.",
    };
  revalidatePath("/clientes");
  redirect("/clientes");
}
