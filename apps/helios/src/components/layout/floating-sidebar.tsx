"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTranslations } from "next-intl"
import {
  BarChart3,
  Globe,
  BookOpen,
  Shield,
  Plus,
  Search,
  Settings,
} from "lucide-react"
import { cn } from "@/lib/utils"

const mainNavItems = [
  { href: "/rankings", labelKey: "rankings" as const, icon: BarChart3 },
  { href: "/market", labelKey: "market" as const, icon: Globe },
  { href: "/learn", labelKey: "learn" as const, icon: BookOpen },
]

const bottomNavItems = [
  { href: "/admin", labelKey: "admin" as const, icon: Shield },
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
        "flex flex-col rounded-xl bg-card text-card-foreground",
        "shadow-[0_2px_8px_rgba(0,0,0,0.04)]",
        "transition-transform duration-[220ms] ease-out",
        open ? "translate-x-0" : "-translate-x-[calc(100%+16px)]",
      )}
    >
      {/* ─── Top actions ─── */}
      <div className="shrink-0 p-2 space-y-1.5">
        <Link
          href="/rankings"
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium bg-accent hover:bg-accent/80 transition-colors"
        >
          <Plus className="h-4 w-4" />
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

      {/* ─── Content zone (scrollable) ─── */}
      <nav className="flex-1 overflow-y-auto px-2 py-1">
        <p className="px-2 mb-1 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground/60">
          {t("navigation")}
        </p>

        <div className="space-y-0.5">
          {mainNavItems.map(({ href, labelKey, icon: Icon }) => {
            const active = pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2.5 px-2.5 py-[7px] rounded-md text-sm transition-colors",
                  active
                    ? "bg-accent text-foreground font-medium"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="truncate">{t(labelKey)}</span>
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
              className={cn(
                "flex items-center gap-2.5 px-2.5 py-[7px] rounded-md text-sm transition-colors",
                active
                  ? "bg-accent text-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{t(labelKey)}</span>
            </Link>
          )
        })}

        <Link
          href="/admin/settings"
          className="flex items-center gap-2.5 px-2.5 py-[7px] rounded-md text-sm transition-colors text-muted-foreground hover:bg-accent/60 hover:text-foreground"
        >
          <Settings className="h-4 w-4 shrink-0" />
          <span className="truncate">{t("settings")}</span>
        </Link>
      </div>
    </aside>
  )
}
