import "server-only";
import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";
import { supabaseConfig } from "@/lib/config";
import type { Database } from "@/lib/database.types";

export async function createClient() {
  const config = supabaseConfig();
  if (!config)
    throw new Error("Supabase não configurado. Consulte web/README.md.");
  const store = await cookies();
  return createServerClient<Database>(config.url, config.key, {
    cookies: {
      getAll: () => store.getAll(),
      setAll(values) {
        try {
          values.forEach(({ name, value, options }) =>
            store.set(name, value, options),
          );
        } catch {
          // Server Components não escrevem cookies; o proxy renova a sessão.
        }
      },
    },
  });
}
