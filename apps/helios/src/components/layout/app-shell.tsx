import { FloatingSidebar } from "./floating-sidebar";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { LanguageToggle } from "@/components/i18n/language-toggle";
import { Toaster } from "@/components/ui/sonner";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <FloatingSidebar />
      <div className="ml-[80px]">
        <header className="flex items-center justify-end gap-2 px-6 py-3 border-b border-border">
          <LanguageToggle />
          <ThemeToggle />
        </header>
        <main className="p-6">{children}</main>
      </div>
      <Toaster />
    </div>
  );
}
