import { afterEach, describe, expect, it, vi } from "vitest";
import { supabaseConfig } from "./config";
afterEach(() => vi.unstubAllEnvs());
describe("configuração Supabase", () => {
  it("indica ausência de configuração sem inventar credenciais", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    expect(supabaseConfig()).toBeNull();
  });
  it("aceita API local e exige TLS para API remota", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54321");
    expect(supabaseConfig()?.url).toBe("http://127.0.0.1:54321");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://projeto.supabase.co");
    expect(supabaseConfig()).toBeNull();
  });
  it("rejeita chaves privilegiadas na configuração pública", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://projeto.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "sb_secret_test");
    expect(supabaseConfig()).toBeNull();
    vi.stubEnv(
      "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
      `e30.${Buffer.from(JSON.stringify({ role: "service_role" })).toString("base64url")}.signature`,
    );
    expect(supabaseConfig()).toBeNull();
  });
});
