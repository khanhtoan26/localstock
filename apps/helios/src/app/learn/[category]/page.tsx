import { notFound } from "next/navigation";
import { TrendingUp, Calculator, Globe } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { getEntriesByCategory, type GlossaryCategory } from "@/lib/glossary";
import { GlossarySearch } from "@/components/learn/glossary-search";

const VALID_CATEGORIES: GlossaryCategory[] = ["technical", "fundamental", "macro"];

const CATEGORY_META: Record<GlossaryCategory, { title: string; desc: string; icon: typeof TrendingUp }> = {
  technical: { title: "Chỉ Báo Kỹ Thuật", desc: "Các chỉ báo phân tích xu hướng và động lượng giá cổ phiếu", icon: TrendingUp },
  fundamental: { title: "Tỷ Số Cơ Bản", desc: "Các chỉ số đánh giá sức khỏe tài chính và định giá doanh nghiệp", icon: Calculator },
  macro: { title: "Yếu Tố Vĩ Mô", desc: "Các chỉ số kinh tế vĩ mô ảnh hưởng đến thị trường chứng khoán", icon: Globe },
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
  const meta = CATEGORY_META[validCategory];
  const Icon = meta.icon;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <Icon className="h-6 w-6 text-primary" />
        <h1 className="text-lg font-semibold">{meta.title}</h1>
      </div>
      <div className="flex items-center gap-2 mb-6">
        <Badge variant="outline">{entries.length} mục</Badge>
        <span className="text-sm text-muted-foreground">{meta.desc}</span>
      </div>
      <GlossarySearch entries={entries} category={validCategory} />
    </div>
  );
}
