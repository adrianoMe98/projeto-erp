import Link from "next/link";
import { requireAccess } from "@/lib/auth";
import { logout } from "@/app/login/actions";

export const dynamic = "force-dynamic";

export default async function Workspace({
  children,
}: {
  children: React.ReactNode;
}) {
  const { perfil } = await requireAccess();
  return (
    <div className="workspace">
      <aside className="sidebar">
        <Link className="brand" href="/clientes">
          ERP<span>GESTÃO E OPERAÇÕES</span>
        </Link>
        <div className="nav-title">ÁREA DE TRABALHO</div>
        <Link className="nav-link active" href="/clientes">
          ◉{" "}
          <span>
            {perfil.papel === "cliente" ? "Minha empresa" : "Clientes"}
          </span>
        </Link>
        <div className="sidebar-note">
          Uma base organizada
          <br />
          para crescer com você.
        </div>
      </aside>
      <div className="workspace-main">
        <header className="topbar">
          <span>Gestão de clientes</span>
          <div>
            <span className="avatar">
              {perfil.nome.slice(0, 1).toUpperCase()}
            </span>
            <span>{perfil.nome}</span>
            <form action={logout}>
              <button className="text-button">Sair</button>
            </form>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
