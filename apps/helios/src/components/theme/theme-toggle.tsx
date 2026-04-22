"use client";
import { useSyncExternalStore } from "react";
import { useTheme } from "@/components/theme/theme-provider";
import { useTranslations } from "next-intl";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";

const emptySubscribe = () => () => {};
function useMounted() {
  return useSyncExternalStore(emptySubscribe, () => true, () => false);
}

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const t = useTranslations("theme");
  const mounted = useMounted();

  // Render a placeholder during SSR/hydration to avoid mismatch
  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" aria-label={t("switchToDark")}>
        <Moon className="h-4 w-4" />
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      aria-label={
        resolvedTheme === "dark"
          ? t("switchToLight")
          : t("switchToDark")
      }
    >
      {resolvedTheme === "dark" ? (
        <Sun className="h-4 w-4" />
      ) : (
        <Moon className="h-4 w-4" />
      )}
    </Button>
  );
}
