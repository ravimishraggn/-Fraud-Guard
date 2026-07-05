"use client";

import KPICard from "@/components/dashboard/KPICard";
import RecentFlags from "@/components/dashboard/RecentFlags";
import SavingsChart from "@/components/dashboard/SavingsChart";
import PageWrapper from "@/components/layout/PageWrapper";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import { api } from "@/lib/api";
import { TEXT } from "@/lib/constants";
import { formatPaise } from "@/lib/utils";
import { AnalyticsSummary, DocumentList, TrendPoint } from "@/types";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

export default function DashboardPage() {
  const summary = useQuery<AnalyticsSummary>({
    queryKey: ["analytics", "summary"],
    queryFn: async () => (await api.get("/api/v1/analytics/summary")).data,
  });
  const trends = useQuery<{ series: TrendPoint[] }>({
    queryKey: ["analytics", "trends"],
    queryFn: async () => (await api.get("/api/v1/analytics/trends")).data,
  });
  const flagged = useQuery<DocumentList>({
    queryKey: ["documents", "review-recent"],
    queryFn: async () =>
      (await api.get("/api/v1/documents", { params: { status: "REVIEW_REQUIRED", page_size: 5 } }))
        .data,
  });

  if (summary.isLoading) {
    return (
      <PageWrapper title={TEXT.dashboard.title}>
        <Spinner label={TEXT.common.loading} />
      </PageWrapper>
    );
  }

  if (summary.isError || !summary.data) {
    return (
      <PageWrapper title={TEXT.dashboard.title}>
        <Card>
          <p className="text-sm text-danger">{TEXT.common.error}</p>
        </Card>
      </PageWrapper>
    );
  }

  const s = summary.data;

  return (
    <PageWrapper title={TEXT.dashboard.title}>
      {s.pending_review > 0 && (
        <div className="mb-4 flex flex-col gap-2 rounded-xl border border-orange-300 bg-orange-50 p-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm font-medium text-medium">
            ⚠️ {TEXT.dashboard.pendingAlert(s.pending_review)}
          </p>
          <Link href="/review" className="text-sm font-semibold text-accent hover:underline">
            {TEXT.dashboard.reviewNow} →
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard label={TEXT.dashboard.docsThisMonth} value={s.documents_this_month} />
        <KPICard label={TEXT.dashboard.flagsRaised} value={s.fraud_flags_raised} accent="text-medium" />
        <KPICard label={TEXT.dashboard.moneySaved} value={formatPaise(s.money_saved_paise)} accent="text-clean" />
        <KPICard label={TEXT.dashboard.automationRate} value={`${s.automation_rate}%`} accent="text-accent" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title={TEXT.dashboard.volumeChart} className="lg:col-span-2">
          {trends.data ? <SavingsChart data={trends.data.series} /> : <Spinner />}
        </Card>
        <Card title={TEXT.dashboard.recentFlags}>
          {flagged.isLoading ? <Spinner /> : <RecentFlags documents={flagged.data?.items ?? []} />}
        </Card>
      </div>
    </PageWrapper>
  );
}
