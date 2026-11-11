import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ERP · Gestão",
  description: "Gestão de clientes e operações",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
