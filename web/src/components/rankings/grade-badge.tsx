import { gradeColors } from "@/lib/utils";

export function GradeBadge({ grade }: { grade: string }) {
  const colors = gradeColors[grade] || gradeColors.F;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold border ${colors}`}>
      {grade}
    </span>
  );
}
