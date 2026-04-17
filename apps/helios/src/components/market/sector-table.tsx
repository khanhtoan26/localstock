import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { GradeBadge } from "@/components/rankings/grade-badge";
import { formatScore } from "@/lib/utils";
import type { SectorPerformance } from "@/lib/types";

/** Convert avg_score to grade letter */
function scoreToGrade(score: number): string {
  if (score >= 80) return "A";
  if (score >= 60) return "B";
  if (score >= 40) return "C";
  if (score >= 20) return "D";
  return "F";
}

interface SectorTableProps {
  sectors: SectorPerformance[];
}

export function SectorTable({ sectors }: SectorTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="text-xs">Ngành</TableHead>
          <TableHead className="text-xs w-[80px]">Điểm TB</TableHead>
          <TableHead className="text-xs w-[60px]">Số Mã</TableHead>
          <TableHead className="text-xs w-[60px]">Hạng</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sectors.map((sector) => (
          <TableRow key={sector.group_code}>
            <TableCell className="text-sm">{sector.group_name_vi}</TableCell>
            <TableCell className="font-mono text-sm">{formatScore(sector.avg_score)}</TableCell>
            <TableCell className="font-mono text-sm">{sector.stock_count}</TableCell>
            <TableCell>
              <GradeBadge grade={scoreToGrade(sector.avg_score)} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
