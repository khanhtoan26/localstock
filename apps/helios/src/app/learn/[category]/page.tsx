import { notFound } from "next/navigation";
import { TrendingUp, Calculator, Globe } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { Badge } from "@/components/ui/badge";
import { getEntriesByCategory, type GlossaryCategory } from "@/lib/glossary";
import { GlossarySearch } from "@/components/learn/glossary-search";

const VALID_CATEGORIES: GlossaryCategory[] = ["technical", "fundamental", "macro"];

const CATEGORY_ICONS: Record<GlossaryCategory, typeof TrendingUp> = {
  technical: TrendingUp,
  fundamental: Calculator,
  macro: Globe,
};

// Static generation: build all 3 category pages at build time
export function generateStaticParams() {
  return VALID_CATEGORIES.map((category) => ({ category }));
}

export default async function LearnCategoryPage({
  params,
}: {
  params: Promise<{ category: string }>;
}) {
  const { category } = await params;

  if (!VALID_CATEGORIES.includes(category as GlossaryCategory)) {
    notFound();
  }

  const validCategory = category as GlossaryCategory;
  const entries = getEntriesByCategory(validCategory);
  const Icon = CATEGORY_ICONS[validCategory];
  const t = await getTranslations("learn");

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <Icon className="h-6 w-6 text-primary" />
        <h1 className="text-lg font-semibold">{t(`categories.${validCategory}.title`)}</h1>
      </div>
      <div className="flex items-center gap-2 mb-6">
        <Badge variant="outline">{entries.length} {t("entries")}</Badge>
        <span className="text-sm text-muted-foreground">{t(`categories.${validCategory}.desc`)}</span>
      </div>
      <GlossarySearch entries={entries} category={validCategory} />
    </div>
  );
}
