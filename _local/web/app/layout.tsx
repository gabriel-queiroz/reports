import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Reports B2B — console",
  description: "Console de teste do agente de relatórios B2B",
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
