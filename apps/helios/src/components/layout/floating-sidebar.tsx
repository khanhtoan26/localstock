"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTranslations } from "next-intl"
import { BarChart3, Globe, BookOpen, Shield } from "lucide-react"
import { cn } from "@/lib/utils"
import { useSidebarState } from "@/hooks/use-sidebar-state"
import {
  Tooltip,
  TooltipTrigger,
  TooltipPortal,
  TooltipPositioner,
  TooltipContent,
} from "@/components/ui/tooltip"

const mainNavItems = [
  { href: "/rankings", labelKey: "rankings" as const, icon: BarChart3 },
  { href: "/market", labelKey: "market" as const, icon: Globe },
  { href: "/learn", labelKey: "learn" as const, icon: BookOpen },
]

const adminNavItems = [
  { href: "/admin", labelKey: "admin" as const, icon: Shield },
]

export function FloatingSidebar() {
  const pathname = usePathname()
  const t = useTranslations("nav")
  const { collapsed, toggle } = useSidebarState()

  const handleNavClick = () => {
    if (!collapsed) {
      toggle()
    }
  }

  return (
    <>
      {/* Icon Rail — always visible */}
      <aside className="fixed left-0 top-0 h-screen w-14 z-30 flex flex-col items-center py-3 border-r border-sidebar-border bg-sidebar">
        {/* Main nav group */}
        <nav className="flex flex-col items-center gap-1">
          {mainNavItems.map(({ href, labelKey, icon: Icon }) => {
            const active = pathname.startsWith(href)
            return (
              <Tooltip key={href}>
                <TooltipTrigger
                  delay={200}
                  render={
                    <Link
                      href={href}
                      onClick={collapsed ? toggle : handleNavClick}
                      className={cn(
                        "flex items-center justify-center w-10 h-10 rounded-md",
                        active
                          ? "bg-sidebar-accent text-sidebar-primary"
                          : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground",
                      )}
                    />
                  }
                >
                  <Icon className="h-5 w-5" />
                </TooltipTrigger>
                {collapsed && (
                  <TooltipPortal>
                    <TooltipPositioner side="right" sideOffset={8}>
                      <TooltipContent>{t(labelKey)}</TooltipContent>
                    </TooltipPositioner>
                  </TooltipPortal>
                )}
              </Tooltip>
            )
          })}
        </nav>

        {/* Spacer — pushes Admin to bottom */}
        <div className="flex-1" />

        {/* Separator */}
        <div className="w-8 border-t border-sidebar-border mb-2" />

        {/* Admin group — pinned to bottom */}
        <nav className="flex flex-col items-center gap-1 mb-2">
          {adminNavItems.map(({ href, labelKey, icon: Icon }) => {
            const active = pathname.startsWith(href)
            return (
              <Tooltip key={href}>
                <TooltipTrigger
                  delay={200}
                  render={
                    <Link
                      href={href}
                      onClick={collapsed ? toggle : handleNavClick}
                      className={cn(
                        "flex items-center justify-center w-10 h-10 rounded-md",
                        active
                          ? "bg-sidebar-accent text-sidebar-primary"
                          : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground",
                      )}
                    />
                  }
                >
                  <Icon className="h-5 w-5" />
                </TooltipTrigger>
                {collapsed && (
                  <TooltipPortal>
                    <TooltipPositioner side="right" sideOffset={8}>
                      <TooltipContent>{t(labelKey)}</TooltipContent>
                    </TooltipPositioner>
                  </TooltipPortal>
                )}
              </Tooltip>
            )
          })}
        </nav>
      </aside>

      {/* Overlay Panel — always in DOM, visibility via CSS transform */}
      <aside
        className={cn(
          "fixed left-14 top-0 h-screen w-60 z-40",
          "border-r border-sidebar-border bg-sidebar shadow-lg",
          "transition-transform duration-[180ms] ease-out",
          collapsed ? "-translate-x-full" : "translate-x-0",
        )}
        aria-hidden={collapsed}
      >
        {/* Header — only in expanded state (D-02) */}
        <div className="p-4 border-b border-sidebar-border">
          <h1 className="text-lg font-bold text-sidebar-primary">
            LocalStock
          </h1>
          <p className="text-xs text-muted-foreground">AI Stock Agent</p>
        </div>

        {/* Full nav with labels */}
        <nav className="flex-1 p-2 space-y-1">
          {[...mainNavItems, ...adminNavItems].map(
            ({ href, labelKey, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                onClick={handleNavClick}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm",
                  pathname.startsWith(href)
                    ? "bg-sidebar-accent text-sidebar-primary"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent",
                )}
              >
                <Icon className="h-4 w-4" />
                {t(labelKey)}
              </Link>
            ),
          )}
        </nav>
      </aside>
    </>
  )
}
