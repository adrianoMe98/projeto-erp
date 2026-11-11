import type { ClienteInput } from "./database.types";

export type FormState = { error?: string; values?: Record<string, string> };
export function parseCliente(form: FormData): ClienteInput {
  const read = (name: string) => String(form.get(name) ?? "").trim();
  const nome_fantasia = read("nome_fantasia");
  const razao_social = read("razao_social");
  const contato_principal = read("contato_principal");
  const cnpj = read("cnpj")
    .replace(/[.\-\/\s]/g, "")
    .toUpperCase();
  const email = read("email");
  const telefone = read("telefone");
  if (!nome_fantasia || nome_fantasia.length > 150)
    throw new Error("Informe um nome de até 150 caracteres.");
  if (!contato_principal || contato_principal.length > 100)
    throw new Error("Informe o contato principal (até 100 caracteres).");
  if (!/^[A-Z0-9]{12}[0-9]{2}$/.test(cnpj))
    throw new Error(
      "Informe um CNPJ com 14 caracteres, terminando em dois dígitos.",
    );
  if (razao_social.length > 150 || telefone.length > 30)
    throw new Error("Razão social ou telefone excede o tamanho permitido.");
  if (
    email.length > 254 ||
    (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
  )
    throw new Error("Informe um e-mail válido.");
  return {
    nome_fantasia,
    razao_social,
    contato_principal,
    cnpj,
    email,
    telefone,
    ativo: form.get("ativo") === "on",
  };
}

export function formatCnpj(value: string) {
  return value.replace(/^(.{2})(.{3})(.{3})(.{4})(.{2})$/, "$1.$2.$3/$4-$5");
}
