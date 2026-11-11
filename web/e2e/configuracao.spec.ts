import { expect, test } from "@playwright/test";
// Fluxo sem credenciais. Execute com as duas NEXT_PUBLIC_SUPABASE_* vazias.
for (const colorScheme of ["light", "dark"] as const) {
  test(`acesso sem configuração, tema ${colorScheme}`, async ({ page }) => {
    await page.emulateMedia({ colorScheme });
    await page.goto("/");
    await expect(
      page.getByText("Ambiente em preparação", { exact: false }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Acessar minha conta" }).click();
    await expect(
      page.getByRole("heading", { name: "Acesse sua conta" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Entrar na plataforma/ }),
    ).toBeDisabled();
    await page.goto("/clientes/novo");
    await expect(page).toHaveURL("http://127.0.0.1:3000/");
  });
}
