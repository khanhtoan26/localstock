"use client"

import { Sidebar } from "./floating-sidebar";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { LanguageToggle } from "@/components/i18n/language-toggle";
import { Toaster } from "@/components/ui/sonner";
import { useSidebarState } from "@/hooks/use-sidebar-state";
import { useTranslations } from "next-intl";
import { PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { collapsed, toggle } = useSidebarState();
  const sidebarOpen = !collapsed;
  const ts = useTranslations("sidebar");

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* ─── Top header (full-width, fixed) ─── */}
      <header className="shrink-0 h-12 flex items-center justify-between px-4 border-b border-border bg-card z-40">
        <div className="flex items-center gap-3">
          <button
            onClick={toggle}
            title={sidebarOpen ? ts("collapse") : ts("expand")}
            className="p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
          <div className="flex items-baseline gap-1.5">
            <span className="text-sm font-bold">{ts("appName")}</span>
            <span className="text-[11px] text-muted-foreground hidden sm:inline">
              {ts("appSubtitle")}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </header>

      {/* ─── Body (sidebar + main) ─── */}
      <div className="flex-1 relative overflow-hidden">
        {/* Sidebar (fixed below header, slides in/out) */}
        <Sidebar open={sidebarOpen} />

        {/* Main content (push pattern: margin-left when sidebar open) */}
        <main
          className={cn(
            "h-full overflow-y-auto p-6 transition-[margin-left] duration-[220ms] ease-out",
            sidebarOpen ? "ml-[260px]" : "ml-0",
          )}
        >
          {children}
        </main>
      </div>

      <Toaster />
    </div>
  );
}
