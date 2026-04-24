import { FloatingSidebar } from "./floating-sidebar";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { LanguageToggle } from "@/components/i18n/language-toggle";
import { Toaster } from "@/components/ui/sonner";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen p-3 gap-2 bg-[#F0EDE8]">
      <FloatingSidebar />
      <div className="flex-1 flex flex-col overflow-auto bg-white rounded-xl shadow-[0_2px_12px_rgba(0,0,0,0.06)] text-foreground">
        <header className="flex items-center justify-end gap-2 px-6 py-3 border-b border-border">
          <LanguageToggle />
          <ThemeToggle />
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
      <Toaster />
    </div>
  );
}
