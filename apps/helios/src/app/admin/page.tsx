"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StockTable } from "@/components/admin/stock-table";
import { PipelineControl } from "@/components/admin/pipeline-control";
import { JobMonitor } from "@/components/admin/job-monitor";

export default function AdminPage() {
  const t = useTranslations("admin");
  const [activeTab, setActiveTab] = useState("stocks");

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">{t("title")}</h1>
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="line">
          <TabsTrigger value="stocks">{t("tabs.stocks")}</TabsTrigger>
          <TabsTrigger value="pipeline">{t("tabs.pipeline")}</TabsTrigger>
          <TabsTrigger value="jobs">{t("tabs.jobs")}</TabsTrigger>
        </TabsList>
        <TabsContent value="stocks" className="pt-6">
          <StockTable />
        </TabsContent>
        <TabsContent value="pipeline" className="pt-6">
          <PipelineControl onOperationTriggered={() => setActiveTab("jobs")} />
        </TabsContent>
        <TabsContent value="jobs" className="pt-6">
          <JobMonitor />
        </TabsContent>
      </Tabs>
    </div>
  );
}
