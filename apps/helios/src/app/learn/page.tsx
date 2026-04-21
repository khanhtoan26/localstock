import Link from "next/link";
import { TrendingUp, Calculator, Globe } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getEntriesByCategory } from "@/lib/glossary";

const categoryConfig = [
  { slug: "technical" as const, icon: TrendingUp },
  { slug: "fundamental" as const, icon: Calculator },
  { slug: "macro" as const, icon: Globe },
] as const;

export default async function LearnPage() {
  const t = await getTranslations("learn");

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <p className="text-sm text-muted-foreground mt-2">
        {t("subtitle")}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
        {categoryConfig.map(({ slug, icon: Icon }) => {
          const count = getEntriesByCategory(slug).length;
          return (
            <Link key={slug} href={`/learn/${slug}`} className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl">
              <Card className="h-full hover:ring-2 hover:ring-primary/20 hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader>
                  <Icon className="h-8 w-8 text-primary" />
                  <CardTitle className="text-lg">{t(`categories.${slug}.title`)}</CardTitle>
                  <p className="text-xs text-muted-foreground">{t(`categories.${slug}.titleEn`)}</p>
                  <Badge variant="outline">{count} {t("entries")}</Badge>
                  <CardDescription>{t(`categories.${slug}.desc`)}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
