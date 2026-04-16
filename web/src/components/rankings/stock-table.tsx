"use client";
import { useRouter } from "next/navigation";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { GradeBadge } from "./grade-badge";
import { formatScore } from "@/lib/utils";
import type { StockScore } from "@/lib/types";
import { useState } from "react";

type SortKey = keyof StockScore;
type SortDir = "asc" | "desc";

interface StockTableProps {
  data: StockScore[];
}

export function StockTable({ data }: StockTableProps) {
  const router = useRouter();
  const [sortKey, setSortKey] = useState<SortKey>("total_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sorted = [...data].sort((a, b) => {
    const aVal = a[sortKey] ?? -Infinity;
    const bVal = b[sortKey] ?? -Infinity;
    if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
    if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  const sortIndicator = (key: SortKey) =>
    sortKey === key ? (sortDir === "asc" ? " ↑" : " ↓") : "";

  const columns: { key: SortKey; header: string; width: string }[] = [
    { key: "rank", header: "#", width: "w-[50px]" },
    { key: "symbol", header: "Mã CK", width: "w-[80px]" },
    { key: "total_score", header: "Điểm", width: "w-[70px]" },
    { key: "grade", header: "Hạng", width: "w-[60px]" },
    { key: "technical_score", header: "Kỹ Thuật", width: "w-[80px]" },
    { key: "fundamental_score", header: "Cơ Bản", width: "w-[80px]" },
    { key: "sentiment_score", header: "Tin Tức", width: "w-[80px]" },
    { key: "macro_score", header: "Vĩ Mô", width: "w-[80px]" },
  ];

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((col) => (
            <TableHead
              key={col.key}
              className={`${col.width} cursor-pointer select-none text-xs hover:text-foreground`}
              onClick={() => handleSort(col.key)}
            >
              {col.header}{sortIndicator(col.key)}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((stock) => (
          <TableRow
            key={stock.symbol}
            className="cursor-pointer hover:bg-muted/50"
            onClick={() => router.push(`/stock/${stock.symbol}`)}
          >
            <TableCell className="font-mono text-sm">{stock.rank}</TableCell>
            <TableCell className="text-primary font-medium text-sm hover:underline">
              {stock.symbol}
            </TableCell>
            <TableCell className="font-mono text-sm">{formatScore(stock.total_score)}</TableCell>
            <TableCell><GradeBadge grade={stock.grade} /></TableCell>
            <TableCell className="font-mono text-sm">{formatScore(stock.technical_score)}</TableCell>
            <TableCell className="font-mono text-sm">{formatScore(stock.fundamental_score)}</TableCell>
            <TableCell className="font-mono text-sm">{formatScore(stock.sentiment_score)}</TableCell>
            <TableCell className="font-mono text-sm">{formatScore(stock.macro_score)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
