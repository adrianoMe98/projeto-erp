export function supabaseConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim();
  if (!url || !key) return null;
  try {
    const parsed = new URL(url);
    const local = ["localhost", "127.0.0.1", "[::1]"].includes(parsed.hostname);
    if (parsed.protocol !== "https:" && !(local && parsed.protocol === "http:"))
      return null;
    if (key.startsWith("sb_secret_")) return null;
    // Chaves anon legadas são aceitas; service_role nunca pode chegar ao browser.
    if (key.split(".").length === 3) {
      const payload = JSON.parse(
        Buffer.from(key.split(".")[1], "base64url").toString(),
      );
      if (payload.role !== "anon") return null;
    }
    return { url: parsed.origin, key };
  } catch {
    return null;
  }
}
