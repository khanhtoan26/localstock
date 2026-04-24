"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTranslations } from "next-intl"
import {
  BarChart3,
  Globe,
  BookOpen,
  Shield,
  PanelLeftClose,
  PanelLeft,
  Plus,
  Search,
  Settings,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useSidebarState } from "@/hooks/use-sidebar-state"

const mainNavItems = [
  { href: "/rankings", labelKey: "rankings" as const, icon: BarChart3 },
  { href: "/market", labelKey: "market" as const, icon: Globe },
  { href: "/learn", labelKey: "learn" as const, icon: BookOpen },
]

const bottomNavItems = [
  { href: "/admin", labelKey: "admin" as const, icon: Shield },
]

export function Sidebar() {
  const pathname = usePathname()
  const t = useTranslations("nav")
  const ts = useTranslations("sidebar")
  const { collapsed, toggle } = useSidebarState()

  return (
    <aside
      className={cn(
        "shrink-0 h-full flex flex-col transition-[width] duration-200 ease-in-out overflow-hidden",
        "bg-sidebar text-sidebar-foreground",
        collapsed ? "w-[60px]" : "w-[260px]",
      )}
    >
      {/* ─── Header zone ─── */}
      <div className="shrink-0 p-2 space-y-1.5">
        {/* Logo + collapse toggle */}
        <div className="flex items-center justify-between px-2 py-1.5">
          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-sm font-bold truncate">{ts("appName")}</h1>
              <p className="text-[11px] text-muted-foreground truncate">
                {ts("appSubtitle")}
              </p>
            </div>
          )}
          <button
            onClick={toggle}
            title={collapsed ? ts("expand") : ts("collapse")}
            className="shrink-0 p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          >
            {collapsed ? (
              <PanelLeft className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* New Analysis button */}
        {!collapsed ? (
          <Link
            href="/rankings"
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium bg-accent hover:bg-accent/80 transition-colors"
          >
            <Plus className="h-4 w-4" />
            {t("newAnalysis")}
          </Link>
        ) : (
          <Link
            href="/rankings"
            title={t("newAnalysis")}
            className="flex items-center justify-center w-full p-2 rounded-lg bg-accent hover:bg-accent/80 transition-colors"
          >
            <Plus className="h-4 w-4" />
          </Link>
        )}

        {/* Search */}
        {!collapsed ? (
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder={t("searchStocks")}
              className="w-full pl-8 pr-8 py-1.5 rounded-md text-xs bg-accent/50 border-none outline-none placeholder:text-muted-foreground/60 focus:bg-accent transition-colors"
            />
            <kbd className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-muted-foreground/50 font-mono">
              ⌘K
            </kbd>
          </div>
        ) : (
          <button
            title={t("searchStocks")}
            className="flex items-center justify-center w-full p-2 rounded-lg hover:bg-accent transition-colors text-muted-foreground"
          >
            <Search className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* ─── Content zone (scrollable) ─── */}
      <nav className="flex-1 overflow-y-auto px-2 py-1">
        {/* Section label */}
        {!collapsed && (
          <p className="px-2 mb-1 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground/60">
            {t("navigation")}
          </p>
        )}

        <div className="space-y-0.5">
          {mainNavItems.map(({ href, labelKey, icon: Icon }) => {
            const active = pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                title={collapsed ? t(labelKey) : undefined}
                className={cn(
                  "flex items-center rounded-md text-sm transition-colors",
                  collapsed
                    ? "justify-center p-2"
                    : "gap-2.5 px-2.5 py-[7px]",
                  active
                    ? "bg-accent text-foreground font-medium"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && <span className="truncate">{t(labelKey)}</span>}
              </Link>
            )
          })}
        </div>
      </nav>

      {/* ─── Footer zone ─── */}
      <div className="shrink-0 border-t border-border px-2 py-1.5 space-y-0.5">
        {bottomNavItems.map(({ href, labelKey, icon: Icon }) => {
          const active = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? t(labelKey) : undefined}
              className={cn(
                "flex items-center rounded-md text-sm transition-colors",
                collapsed
                  ? "justify-center p-2"
                  : "gap-2.5 px-2.5 py-[7px]",
                active
                  ? "bg-accent text-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{t(labelKey)}</span>}
            </Link>
          )
        })}

        <Link
          href="/admin/settings"
          title={collapsed ? t("settings") : undefined}
          className={cn(
            "flex items-center rounded-md text-sm transition-colors",
            collapsed
              ? "justify-center p-2"
              : "gap-2.5 px-2.5 py-[7px]",
            "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
          )}
        >
          <Settings className="h-4 w-4 shrink-0" />
          {!collapsed && <span className="truncate">{t("settings")}</span>}
        </Link>
      </div>
    </aside>
  )
}
