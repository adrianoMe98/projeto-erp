import Link from "next/link";
import { supabaseConfig } from "@/lib/config";
import { LoginForm } from "./login-form";

export const dynamic = "force-dynamic";
export default function Login() {
  return (
    <main className="login-shell">
      <section className="login-story">
        <Link className="brand" href="/">
          ERP<span>GESTÃO E OPERAÇÕES</span>
        </Link>
        <div>
          <div className="eyebrow">SUA OPERAÇÃO, MAIS PRÓXIMA</div>
          <h1>
            Clareza para
            <br />
            cuidar de cada
            <br />
            <span>conexão.</span>
          </h1>
          <p>
            Organize seus clientes e acompanhe o que importa para a sua equipe.
          </p>
        </div>
        <small>Uma nova etapa para o seu ERP.</small>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <span className="pill">BEM-VINDO DE VOLTA</span>
          <h2>Acesse sua conta</h2>
          <p className="muted">Use o e-mail cadastrado pela sua equipe.</p>
          <LoginForm configured={!!supabaseConfig()} />
          <p className="login-help">
            Precisa de acesso ou de uma nova senha?
            <br />
            Fale com o administrador da sua equipe.
          </p>
        </div>
      </section>
    </main>
  );
}
