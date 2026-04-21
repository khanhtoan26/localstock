import Link from "next/link";
import { TrendingUp, Calculator, Globe } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getEntriesByCategory } from "@/lib/glossary";

const categories = [
  {
    slug: "technical" as const,
    title: "Chỉ Báo Kỹ Thuật",
    titleEn: "Technical Indicators",
    desc: "Các chỉ báo phân tích xu hướng và động lượng giá cổ phiếu",
    icon: TrendingUp,
  },
  {
    slug: "fundamental" as const,
    title: "Tỷ Số Cơ Bản",
    titleEn: "Fundamental Ratios",
    desc: "Các chỉ số đánh giá sức khỏe tài chính và định giá doanh nghiệp",
    icon: Calculator,
  },
  {
    slug: "macro" as const,
    title: "Yếu Tố Vĩ Mô",
    titleEn: "Macro Concepts",
    desc: "Các chỉ số kinh tế vĩ mô ảnh hưởng đến thị trường chứng khoán",
    icon: Globe,
  },
] as const;

export default function LearnPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold">Học — Kiến Thức Đầu Tư</h1>
      <p className="text-sm text-muted-foreground mt-2">
        Tìm hiểu các chỉ báo kỹ thuật, tỷ số cơ bản và yếu tố vĩ mô được sử dụng trong phân tích AI
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
        {categories.map(({ slug, title, titleEn, desc, icon: Icon }) => {
          const count = getEntriesByCategory(slug).length;
          return (
            <Link key={slug} href={`/learn/${slug}`} className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl">
              <Card className="h-full hover:ring-2 hover:ring-primary/20 hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader>
                  <Icon className="h-8 w-8 text-primary" />
                  <CardTitle className="text-lg">{title}</CardTitle>
                  <p className="text-xs text-muted-foreground">{titleEn}</p>
                  <Badge variant="outline">{count} mục</Badge>
                  <CardDescription>{desc}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
