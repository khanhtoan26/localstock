"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTranslations } from "next-intl"
import { BarChart3, Globe, BookOpen, Shield } from "lucide-react"
import { cn } from "@/lib/utils"

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

  return (
    <aside className="w-[220px] shrink-0 h-[calc(100vh-24px)] flex flex-col bg-white rounded-xl shadow-[0_2px_12px_rgba(0,0,0,0.08)]">
      {/* Logo / branding */}
      <div className="px-3.5 py-4 border-b border-[#E5E5E5]">
        <h1 className="text-base font-bold text-[#111]">LocalStock</h1>
        <p className="text-xs text-[#888]">AI Stock Agent</p>
      </div>

      {/* Main nav group */}
      <nav className="flex-1 p-2 space-y-0.5">
        {mainNavItems.map(({ href, labelKey, icon: Icon }) => {
          const active = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg text-sm",
                active
                  ? "bg-[#F0EDE8] text-[#111] font-medium"
                  : "text-[#6B7280] hover:bg-[#F5F5F5] hover:text-[#111]",
              )}
            >
              <Icon className="h-4 w-4" />
              {t(labelKey)}
            </Link>
          )
        })}
      </nav>

      {/* Admin group — bottom */}
      <div className="border-t border-[#E5E5E5] p-2 space-y-0.5">
        {adminNavItems.map(({ href, labelKey, icon: Icon }) => {
          const active = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg text-sm",
                active
                  ? "bg-[#F0EDE8] text-[#111] font-medium"
                  : "text-[#6B7280] hover:bg-[#F5F5F5] hover:text-[#111]",
              )}
            >
              <Icon className="h-4 w-4" />
              {t(labelKey)}
            </Link>
          )
        })}
      </div>
    </aside>
  )
}
