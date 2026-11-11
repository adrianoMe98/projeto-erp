"use client";
import Link from "next/link";
import { useActionState } from "react";
import type { Cliente } from "@/lib/database.types";
import { saveCliente } from "./actions";

export function ClienteForm({ cliente }: { cliente?: Cliente }) {
  const [state, action, pending] = useActionState(
    saveCliente.bind(null, cliente?.id ?? null),
    {},
  );
  return (
    <form action={action} className="form-card">
      <div className="form-heading">
        <h2>Informações do cliente</h2>
        <p>Comece pelos dados que sua equipe usa no dia a dia.</p>
      </div>
      <div className="form-grid">
        <label>
          Nome fantasia
          <input
            name="nome_fantasia"
            defaultValue={cliente?.nome_fantasia}
            required
            maxLength={150}
          />
        </label>
        <label>
          Razão social
          <input
            name="razao_social"
            defaultValue={cliente?.razao_social}
            maxLength={150}
          />
        </label>
        <label>
          CNPJ
          <input
            name="cnpj"
            defaultValue={cliente?.cnpj}
            required
            maxLength={18}
            placeholder="00.000.000/0001-00"
          />
        </label>
        <label>
          Contato principal
          <input
            name="contato_principal"
            defaultValue={cliente?.contato_principal}
            required
            maxLength={100}
          />
        </label>
        <label>
          E-mail
          <input
            name="email"
            type="email"
            defaultValue={cliente?.email}
            maxLength={254}
          />
        </label>
        <label>
          Telefone
          <input
            name="telefone"
            type="tel"
            defaultValue={cliente?.telefone}
            maxLength={30}
          />
        </label>
      </div>
      <label className="check-label">
        <input
          type="checkbox"
          name="ativo"
          defaultChecked={cliente?.ativo ?? true}
        />{" "}
        Cliente ativo
      </label>
      {state.error && (
        <p className="error" role="alert">
          {state.error}
        </p>
      )}
      <div className="form-footer">
        <Link className="button secondary" href="/clientes">
          Cancelar
        </Link>
        <button disabled={pending}>
          {pending ? "Salvando…" : "Salvar cliente"}
        </button>
      </div>
    </form>
  );
}
