// Usa apenas o stack local selecionado pelo config.toml. Não conecta a projetos hospedados.
import { execFileSync, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../../", import.meta.url));
const cli = fileURLToPath(
  new URL("../node_modules/.bin/supabase", import.meta.url),
);
const status = JSON.parse(
  execFileSync(cli, ["status", "--workdir", root, "-o", "json"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "inherit"],
  }),
);
const url = status.API_URL;
if (!status.ANON_KEY || !status.SERVICE_ROLE_KEY)
  throw new Error(
    "O stack local não forneceu as credenciais exigidas pelos testes.",
  );
if (!url || !["127.0.0.1", "localhost"].includes(new URL(url).hostname))
  throw new Error("Os testes só podem usar o Supabase local.");
const result = spawnSync(
  "node_modules/.bin/playwright",
  ["test", "--config", "playwright.integration.config.ts"],
  {
    stdio: "inherit",
    env: {
      ...process.env,
      NEXT_PUBLIC_SUPABASE_URL: url,
      NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: status.ANON_KEY,
      SUPABASE_TEST_SERVICE_KEY: status.SERVICE_ROLE_KEY,
    },
  },
);
process.exit(result.status ?? 1);
