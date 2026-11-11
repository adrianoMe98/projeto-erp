import { describe, expect, it } from "vitest";
import { formatCnpj, parseCliente } from "./clientes";

function form(values: Record<string, string> = {}) {
  const data = new FormData();
  for (const [key, value] of Object.entries({
    nome_fantasia: "Empresa",
    cnpj: "12.345.678/0001-95",
    contato_principal: "Adriano",
    ativo: "on",
    ...values,
  }))
    data.set(key, value);
  return data;
}
describe("cadastro de clientes", () => {
  it("normaliza o documento antes de persistir e comparar duplicados", () => {
    expect(parseCliente(form()).cnpj).toBe("12345678000195");
    expect(formatCnpj("12345678000195")).toBe("12.345.678/0001-95");
  });
  it("aceita CNPJ alfanumérico sem perder as letras", () => {
    expect(parseCliente(form({ cnpj: "ab.cde.fgh/0001-95" })).cnpj).toBe(
      "ABCDEFGH000195",
    );
  });
  it.each(["", "123", "12.345.678/0001-AA", "' OR 1=1"])(
    "rejeita documento inválido: %s",
    (cnpj) => {
      expect(() => parseCliente(form({ cnpj }))).toThrow(/CNPJ/);
    },
  );
  it("permite desativação sem excluir o registro", () => {
    const data = form();
    data.delete("ativo");
    expect(parseCliente(data).ativo).toBe(false);
  });
  it("não aceita campos obrigatórios vazios", () => {
    expect(() => parseCliente(form({ nome_fantasia: "  " }))).toThrow();
    expect(() => parseCliente(form({ contato_principal: "" }))).toThrow();
  });
  it("valida tamanho e e-mail também no servidor", () => {
    expect(() =>
      parseCliente(form({ nome_fantasia: "a".repeat(151) })),
    ).toThrow();
    expect(() => parseCliente(form({ email: "sem-arroba" }))).toThrow();
  });
});
