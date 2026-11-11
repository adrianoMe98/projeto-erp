import { notFound } from "next/navigation";
import { requireAccess } from "@/lib/auth";
import { ClienteForm } from "../../cliente-form";
export default async function EditarCliente({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { supabase } = await requireAccess(true);
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(id)) notFound();
  const { data: cliente, error } = await supabase
    .from("clientes")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw new Error("Não foi possível consultar o cadastro.");
  if (!cliente) notFound();
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">CARTEIRA DE CLIENTES</div>
          <h1>Editar cliente</h1>
          <p className="muted">
            Mantenha as informações da sua carteira atualizadas.
          </p>
        </div>
      </div>
      <ClienteForm cliente={cliente} />
    </>
  );
}
