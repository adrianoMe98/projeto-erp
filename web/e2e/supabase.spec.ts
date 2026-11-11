import { randomBytes, randomUUID } from "node:crypto";
import { createClient } from "@supabase/supabase-js";
import { expect, test, type Page } from "@playwright/test";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
if (!url || !["localhost", "127.0.0.1"].includes(new URL(url).hostname))
  throw new Error("Use scripts/test-supabase.mjs contra o stack local.");
const admin = createClient(url, process.env.SUPABASE_TEST_SERVICE_KEY!, {
  auth: { persistSession: false, autoRefreshToken: false },
});
const suffix = randomUUID().slice(0, 8);
const password = randomBytes(24).toString("base64url");
const users: string[] = [];
const clients: string[] = [];
const teamEmail = `team-${suffix}@example.test`;
const customerEmail = `customer-${suffix}@example.test`;
const pendingEmail = `pending-${suffix}@example.test`;
const companyA = `Empresa A ${suffix}`;
const companyB = `Empresa B ${suffix}`;
function cnpj() {
  return `${Date.now().toString().slice(-10)}${Math.floor(Math.random() * 10000)
    .toString()
    .padStart(4, "0")}`;
}

test.beforeAll(async () => {
  for (const name of [companyA, companyB]) {
    const { data, error } = await admin
      .from("clientes")
      .insert({
        nome_fantasia: name,
        cnpj: cnpj(),
        contato_principal: "Responsável",
      })
      .select("id")
      .single();
    if (error) throw error;
    clients.push(data.id);
  }
  for (const [email, papel, cliente_id] of [
    [teamEmail, "admin", null],
    [customerEmail, "cliente", clients[0]],
    [pendingEmail, null, null],
  ] as const) {
    const { data, error } = await admin.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
    });
    if (error) throw error;
    users.push(data.user.id);
    if (papel) {
      const { error: profileError } = await admin
        .from("perfis")
        .insert({ id: data.user.id, nome: email, papel, cliente_id });
      if (profileError) throw profileError;
    }
  }
});
test.afterAll(async () => {
  for (const id of users) await admin.auth.admin.deleteUser(id);
  if (clients.length) {
    const { error } = await admin.from("clientes").delete().in("id", clients);
    if (error) throw error;
  }
});
async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: /Entrar na plataforma/ }).click();
}

test("equipe autentica, cria, encontra e edita um cadastro", async ({
  page,
}, testInfo) => {
  await login(page, teamEmail);
  await expect(
    page.getByRole("heading", { name: "Seus clientes, em um só lugar." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "+ Novo cliente" }).click();
  const documento = cnpj();
  await page.getByLabel("Nome fantasia").fill(`Novo ${suffix}`);
  await page.getByLabel("CNPJ").fill(documento);
  await page.getByLabel("Contato principal").fill("Responsável novo");
  await page.getByRole("button", { name: "Salvar cliente" }).click();
  await expect(page).toHaveURL(/\/clientes$/);
  const { data } = await admin
    .from("clientes")
    .select("id")
    .eq("cnpj", documento)
    .single();
  if (data) clients.push(data.id);
  await page.getByLabel("Buscar por nome").fill(`Novo ${suffix}`);
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await page.getByRole("link", { name: "Editar →" }).click();
  await page.getByLabel("Nome fantasia").fill(`Atualizado ${suffix}`);
  await page.getByRole("button", { name: "Salvar cliente" }).click();
  await page.getByLabel("Buscar por nome").fill(`Atualizado ${suffix}`);
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(
    page.getByText(`Atualizado ${suffix}`, { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("carteira.png"),
    fullPage: true,
    caret: "initial",
  });
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/clientes");
  await expect(page).toHaveURL(/\/login$/);
});

test("cliente só consulta sua empresa e não acessa criação ou edição", async ({
  page,
}, testInfo) => {
  await login(page, customerEmail);
  await expect(page.getByText(companyA, { exact: true })).toBeVisible();
  await expect(page.getByText(companyB, { exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Novo cliente/ })).toHaveCount(0);
  await page.goto("/clientes/novo");
  await expect(page).toHaveURL(/\/clientes$/);
  await page.goto(`/clientes/${clients[1]}/editar`);
  await expect(page).toHaveURL(/\/clientes$/);
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.getByText(companyA, { exact: true })).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("cliente-escuro.png"),
    fullPage: true,
    caret: "initial",
  });
});

test("conta autenticada sem perfil recebe acesso pendente", async ({
  page,
}) => {
  await login(page, pendingEmail);
  await expect(
    page.getByRole("heading", { name: "Sua conta está criada." }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/acesso-pendente$/);
});
