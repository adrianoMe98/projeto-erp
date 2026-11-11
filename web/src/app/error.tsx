"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="center-card">
      <h1>Não foi possível carregar esta página.</h1>
      <p>Tente novamente. Se o problema continuar, fale com a sua equipe.</p>
      <button onClick={reset}>Tentar novamente</button>
    </main>
  );
}
