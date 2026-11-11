import Link from "next/link";
import { redirect } from "next/navigation";
import { supabaseConfig } from "@/lib/config";

export const dynamic = "force-dynamic";
export default function Home() {
  if (supabaseConfig()) redirect("/clientes");
  return (
    <main className="welcome">
      <div className="brand">
        ERP<span>GESTÃO E OPERAÇÕES</span>
      </div>
      <div className="eyebrow">UMA NOVA BASE PARA O SEU NEGÓCIO</div>
      <h1>
        Gestão conectada.
        <br />
        <span>Do acesso à operação.</span>
      </h1>
      <p className="lede">
        Clientes, equipe e informações no mesmo lugar, com acesso organizado
        para cada pessoa.
      </p>
      <section className="notice">
        <span className="status-dot" />
        Ambiente em preparação
        <p>
          O acesso será liberado após a configuração do serviço e dos perfis da
          equipe.
        </p>
      </section>
      <div className="steps">
        <article>
          <b>01</b>
          <h2>Acesso centralizado</h2>
          <p>Uma conta para entrar e um perfil para definir seu acesso.</p>
        </article>
        <article>
          <b>02</b>
          <h2>Clientes organizados</h2>
          <p>Cadastro, contatos e situação em uma visão única.</p>
        </article>
        <article>
          <b>03</b>
          <h2>Espaço para evoluir</h2>
          <p>A base para os próximos módulos da operação.</p>
        </article>
      </div>
      <footer>
        ERP · Nova plataforma <Link href="/login">Acessar minha conta →</Link>
      </footer>
    </main>
  );
}
