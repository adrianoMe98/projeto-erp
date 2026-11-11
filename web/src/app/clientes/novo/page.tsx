import { requireAccess } from "@/lib/auth";
import { ClienteForm } from "../cliente-form";
export default async function NovoCliente() {
  await requireAccess(true);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">CARTEIRA DE CLIENTES</div>
          <h1>Novo cliente</h1>
          <p className="muted">Uma nova conexão começa com um bom cadastro.</p>
        </div>
      </div>
      <ClienteForm />
    </>
  );
}
