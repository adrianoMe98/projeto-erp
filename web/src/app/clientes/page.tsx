import Link from "next/link";
import { requireAccess } from "@/lib/auth";
import { formatCnpj } from "@/lib/clientes";

export default async function Clientes({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const { supabase, perfil } = await requireAccess();
  const params = await searchParams;
  const search = (typeof params.q === "string" ? params.q : "")
    .trim()
    .slice(0, 100);
  const parsed = Number(params.page ?? 1);
  const page =
    Number.isSafeInteger(parsed) && parsed > 0 && parsed <= 100000 ? parsed : 1;
  const size = 20;
  let query = supabase
    .from("clientes")
    .select("*", { count: "exact" })
    .order("nome_fantasia")
    .order("id");
  if (search)
    query = query.ilike(
      "nome_fantasia",
      `%${search.replace(/[\\%_]/g, "\\$&")}%`,
    );
  const { data, error, count } = await query.range(
    (page - 1) * size,
    page * size - 1,
  );
  if (error) throw new Error("Não foi possível consultar os clientes.");
  const staff = perfil.papel !== "cliente";
  const href = (number: number) =>
    `/clientes?${new URLSearchParams({ q: search, page: String(number) })}`;
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">RELACIONAMENTOS</div>
          <h1>{staff ? "Seus clientes, em um só lugar." : "Minha empresa"}</h1>
          <p className="muted">
            {staff
              ? "Organize informações e mantenha cada contato por perto."
              : "Consulte os dados da sua empresa. Alterações são feitas pela equipe."}
          </p>
        </div>
        {staff && (
          <Link className="button" href="/clientes/novo">
            + Novo cliente
          </Link>
        )}
      </div>
      <section className="stat-card">
        <span>CLIENTES ACESSÍVEIS</span>
        <strong>{count ?? 0}</strong>
        <p>
          {search
            ? "Correspondências para a busca atual"
            : "Cadastros disponíveis para o seu perfil"}
        </p>
      </section>
      <section className="table-card">
        <div className="table-toolbar">
          <h2>{staff ? "Carteira de clientes" : "Dados cadastrais"}</h2>
          <form>
            <label className="sr-only" htmlFor="search">
              Buscar por nome
            </label>
            <input
              id="search"
              name="q"
              defaultValue={search}
              placeholder="Buscar pelo nome…"
              type="search"
            />
            <button className="secondary">Buscar</button>
          </form>
        </div>
        {data?.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Cliente</th>
                  <th>CNPJ</th>
                  <th>Contato principal</th>
                  <th>Situação</th>
                  {staff && (
                    <th>
                      <span className="sr-only">Ações</span>
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {data.map((cliente) => (
                  <tr key={cliente.id}>
                    <td>
                      <strong>{cliente.nome_fantasia}</strong>
                      <small>
                        {cliente.razao_social || cliente.email || "—"}
                      </small>
                    </td>
                    <td>{formatCnpj(cliente.cnpj)}</td>
                    <td>{cliente.contato_principal}</td>
                    <td>
                      <span
                        className={`badge ${cliente.ativo ? "green" : "gray"}`}
                      >
                        {cliente.ativo ? "Ativo" : "Inativo"}
                      </span>
                    </td>
                    {staff && (
                      <td>
                        <Link href={`/clientes/${cliente.id}/editar`}>
                          Editar →
                        </Link>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">
            <div className="empty-icon">◎</div>
            <h3>
              {search
                ? "Nenhum cliente encontrado"
                : "Tudo pronto para começar"}
            </h3>
            <p>
              {search
                ? "Tente buscar por outro nome."
                : staff
                  ? "Cadastre o primeiro cliente para organizar sua carteira."
                  : "Seu cadastro ainda não está disponível. Fale com a equipe."}
            </p>
            {staff && !search && (
              <Link href="/clientes/novo">Cadastrar primeiro cliente →</Link>
            )}
          </div>
        )}
        <div className="pagination">
          <span>
            Página {page} · {count ?? 0} cadastro(s)
          </span>
          <div>
            {page > 1 && <Link href={href(page - 1)}>← Anterior</Link>}
            {page * size < (count ?? 0) && (
              <Link href={href(page + 1)}>Próxima →</Link>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
