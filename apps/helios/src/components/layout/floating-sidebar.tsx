"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTranslations } from "next-intl"
import {
  BarChart3,
  Globe,
  BookOpen,
  Plus,
  Search,
  Settings,
  TrendingUp,
  Star,
  FileText,
  User,
} from "lucide-react"
import { cn } from "@/lib/utils"

const mainNavItems = [
  { href: "/rankings", labelKey: "rankings" as const, icon: BarChart3 },
  { href: "/market", labelKey: "market" as const, icon: Globe },
  { href: "/learn", labelKey: "learn" as const, icon: BookOpen },
]

const sidebarTabs = [
  { id: "screener" as const, href: "/rankings", labelKey: "tabScreener" as const, icon: TrendingUp },
  { id: "watchlist" as const, href: "/market", labelKey: "tabWatchlist" as const, icon: Star },
  { id: "reports" as const, href: "/admin", labelKey: "tabReports" as const, icon: FileText },
]

interface SidebarProps {
  open: boolean
}

export function Sidebar({ open }: SidebarProps) {
  const pathname = usePathname()
  const t = useTranslations("nav")

  return (
    <aside
      className={cn(
        "absolute top-2 left-2 bottom-2 w-[260px] z-30",
        "flex flex-col rounded-[10px] bg-sidebar text-sidebar-foreground",
        "shadow-[0_2px_8px_rgba(0,0,0,0.04)]",
        "transition-transform duration-[220ms] ease-out",
        open ? "translate-x-0" : "-translate-x-[calc(100%+16px)]",
      )}
    >
      {/* ─── New Analysis + Search ─── */}
      <div className="shrink-0 p-2 space-y-1.5">
        <Link
          href="/rankings"
          className="flex items-center gap-2 w-full px-2.5 py-2 rounded-md text-[13px] font-medium bg-accent hover:bg-accent/80 transition-colors"
        >
          <Plus className="h-4 w-4 text-muted-foreground" />
          {t("newAnalysis")}
        </Link>

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
      </div>

      {/* ─── Tab switcher ─── */}
      <div className="shrink-0 px-2 pb-1">
        <div className="flex gap-0.5 justify-center">
          {sidebarTabs.map(({ id, href, labelKey, icon: Icon }) => (
            <Link
              key={id}
              href={href}
              title={t(labelKey)}
              className={cn(
                "flex items-center justify-center p-2 rounded-md transition-colors",
                pathname.startsWith(href)
                  ? "bg-black/[0.05] dark:bg-white/[0.06] text-foreground"
                  : "text-muted-foreground hover:bg-black/[0.03] dark:hover:bg-white/[0.03]",
              )}
            >
              <Icon className="h-4 w-4" />
            </Link>
          ))}
        </div>
      </div>

      {/* ─── Nav items (no section header) ─── */}
      <nav className="px-2 py-1 space-y-0.5">
        {mainNavItems.map(({ href, labelKey, icon: Icon }) => {
          const active = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-2.5 h-8 rounded-md text-[13px] transition-colors",
                active
                  ? "bg-black/[0.05] dark:bg-white/[0.06] text-foreground font-medium"
                  : "text-muted-foreground hover:bg-black/[0.03] dark:hover:bg-white/[0.03] hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4 text-muted-foreground" />
              <span className="truncate">{t(labelKey)}</span>
            </Link>
          )
        })}
      </nav>

      {/* ─── Pinned section ─── */}
      <div className="px-2 pt-3 pb-1">
        <p className="px-2.5 mb-1 text-xs text-muted-foreground">Pinned</p>
        <div className="space-y-0.5">
          <div className="flex items-center gap-2.5 px-2.5 h-8 rounded-md text-[13px] text-muted-foreground/60">
            <Star className="h-4 w-4" />
            <span className="truncate italic">No pinned items</span>
          </div>
        </div>
      </div>

      {/* ─── Recents section (scrollable) ─── */}
      <div className="flex-1 overflow-y-auto px-2 pt-3 pb-1">
        <p className="px-2.5 mb-1 text-xs text-muted-foreground">Recents</p>
        <div className="space-y-0.5">
          <div className="flex items-center gap-2.5 px-2.5 h-8 rounded-md text-[13px] text-muted-foreground/60">
            <span className="truncate italic">No recent activity</span>
          </div>
        </div>
      </div>

      {/* ─── Footer: Avatar + user ─── */}
      <div className="shrink-0 border-t border-border">
        <button className="flex items-center gap-2.5 w-full px-3 py-2.5 text-[13px] text-foreground hover:bg-black/[0.03] dark:hover:bg-white/[0.03] transition-colors">
          <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center">
            <User className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <span className="truncate font-medium">Admin</span>
          <Settings className="h-3.5 w-3.5 text-muted-foreground ml-auto" />
        </button>
      </div>
    </aside>
  )
}
