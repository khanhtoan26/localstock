"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTranslations } from "next-intl"
import { BarChart3, Globe, BookOpen, Shield } from "lucide-react"
import { cn } from "@/lib/utils"
import { useSidebarState } from "@/hooks/use-sidebar-state"

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
    <aside
      className={cn(
        "fixed left-3 top-3 bottom-3 z-30",
        "rounded-xl shadow-md border border-sidebar-border bg-sidebar",
        "flex flex-col overflow-hidden",
        "transition-[width] duration-[180ms] ease-out",
        collapsed ? "w-[56px]" : "w-60",
      )}
    >
      {/* Header — visible only when expanded */}
      <div
        className={cn(
          "border-b border-sidebar-border overflow-hidden transition-opacity duration-[180ms]",
          collapsed ? "h-0 opacity-0 border-b-0" : "p-4 opacity-100",
        )}
      >
        <h1 className="text-lg font-bold text-sidebar-primary whitespace-nowrap">
          LocalStock
        </h1>
        <p className="text-xs text-muted-foreground whitespace-nowrap">
          AI Stock Agent
        </p>
      </div>

      {/* Main nav group */}
      <nav className={cn("flex-1 flex flex-col gap-1", collapsed ? "items-center px-2 pt-3" : "p-2")}>
        {mainNavItems.map(({ href, labelKey, icon: Icon }) => {
          const active = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              onClick={collapsed ? toggle : handleNavClick}
              title={collapsed ? t(labelKey) : undefined}
              className={cn(
                "flex items-center rounded-md text-sm",
                collapsed
                  ? "justify-center w-10 h-10"
                  : "gap-3 px-3 py-2",
                active
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground",
              )}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!collapsed && <span className="whitespace-nowrap">{t(labelKey)}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Separator */}
      <div className={cn("border-t border-sidebar-border", collapsed ? "mx-2" : "mx-2")} />

      {/* Admin group — pinned to bottom */}
      <nav className={cn("flex flex-col gap-1 pb-3", collapsed ? "items-center px-2 pt-2" : "p-2")}>
        {adminNavItems.map(({ href, labelKey, icon: Icon }) => {
          const active = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              onClick={collapsed ? toggle : handleNavClick}
              title={collapsed ? t(labelKey) : undefined}
              className={cn(
                "flex items-center rounded-md text-sm",
                collapsed
                  ? "justify-center w-10 h-10"
                  : "gap-3 px-3 py-2",
                active
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground",
              )}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!collapsed && <span className="whitespace-nowrap">{t(labelKey)}</span>}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
