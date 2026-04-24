"use client"

import { useState, useCallback } from "react"

const STORAGE_KEY = "localstock-sidebar-collapsed"
const DEFAULT_COLLAPSED = true

export function useSidebarState() {
  const [collapsed, setCollapsedRaw] = useState<boolean>(() => {
    if (typeof window === "undefined") return DEFAULT_COLLAPSED
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === null) return DEFAULT_COLLAPSED
    return stored === "true"
  })

  const setCollapsed = useCallback(
    (value: boolean | ((prev: boolean) => boolean)) => {
      setCollapsedRaw((prev) => {
        const next = typeof value === "function" ? value(prev) : value
        localStorage.setItem(STORAGE_KEY, String(next))
        return next
      })
    },
    [],
  )

  const toggle = useCallback(() => {
    setCollapsed((prev) => !prev)
  }, [setCollapsed])

  return { collapsed, setCollapsed, toggle } as const
}
