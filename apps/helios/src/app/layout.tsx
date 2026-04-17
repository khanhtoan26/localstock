import type { Metadata } from "next";
import { AppShell } from "@/components/layout/app-shell";
import { QueryProvider } from "@/lib/query-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "LocalStock — AI Stock Agent",
  description: "AI Stock Agent for Vietnamese Market (HOSE)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className="dark">
      <body>
        <QueryProvider>
          <AppShell>{children}</AppShell>
        </QueryProvider>
      </body>
    </html>
  );
}
