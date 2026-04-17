import { AlertCircle } from "lucide-react";

interface ErrorStateProps {
  heading?: string;
  body?: string;
}

export function ErrorState({
  heading = "Không thể tải dữ liệu",
  body = "Lỗi kết nối đến backend. Kiểm tra server đang chạy tại localhost:8000.",
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <AlertCircle className="h-12 w-12 text-red-700 dark:text-red-400" />
      <h2 className="mt-4 text-lg font-semibold text-foreground">{heading}</h2>
      <p className="mt-2 text-sm text-muted-foreground text-center max-w-md">{body}</p>
    </div>
  );
}
