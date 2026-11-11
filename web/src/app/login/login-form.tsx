"use client";
import { useActionState } from "react";
import { login } from "./actions";

export function LoginForm({ configured }: { configured: boolean }) {
  const [state, action, pending] = useActionState(login, {});
  return (
    <form action={action} className="form-stack">
      <label>
        E-mail
        <input
          name="email"
          type="email"
          autoComplete="username"
          required
          maxLength={254}
          placeholder="voce@empresa.com.br"
        />
      </label>
      <label>
        Senha
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          maxLength={1024}
        />
      </label>
      {state.error && (
        <p className="error" role="alert">
          {state.error}
        </p>
      )}
      {!configured && (
        <p className="notice" role="status">
          O acesso ainda está em preparação.
        </p>
      )}
      <button disabled={pending || !configured}>
        {pending ? "Entrando…" : "Entrar na plataforma →"}
      </button>
    </form>
  );
}
