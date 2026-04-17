"use client";
import { ThemeProvider as NextThemesProvider } from "next-themes";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="claude"
      themes={["claude", "dark"]}
      value={{ claude: "", dark: "dark" }}
      enableSystem={false}
      disableTransitionOnChange
      storageKey="localstock-theme"
    >
      {children}
    </NextThemesProvider>
  );
}
