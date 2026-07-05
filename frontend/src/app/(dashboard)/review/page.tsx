"use client";

import PageWrapper from "@/components/layout/PageWrapper";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import { Table, TBody, THead } from "@/components/ui/Table";
import { api } from "@/lib/api";
import { TEXT } from "@/lib/constants";
import { timeAgo } from "@/lib/utils";
import { DocumentList } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

export default function ReviewQueuePage() {
  const router = useRouter();
  const { data, isLoading, isError } = useQuery<DocumentList>({
    queryKey: ["documents", "review-queue"],
    queryFn: async () =>
      (
        await api.get("/api/v1/documents", {
          params: { status: "REVIEW_REQUIRED", page_size: 100 },
        })
      ).data,
    refetchInterval: 15000,
  });

  return (
    <PageWrapper title={TEXT.review.title}>
      {isLoading && <Spinner label={TEXT.common.loading} />}
      {isError && (
        <Card>
          <p className="text-sm text-danger">{TEXT.common.error}</p>
        </Card>
      )}
      {data && data.items.length === 0 && (
        <Card>
          <p className="py-8 text-center text-sm text-gray-500">✅ {TEXT.review.empty}</p>
        </Card>
      )}
      {data && data.items.length > 0 && (
        <Table>
          <THead
            headers={[
              TEXT.review.columns.vendor,
              TEXT.review.columns.risk,
              "Score",
              TEXT.review.columns.date,
              TEXT.review.columns.waiting,
            ]}
          />
          <TBody>
            {data.items.map((doc) => (
              <tr
                key={doc.id}
                onClick={() => router.push(`/review/${doc.id}`)}
                className="cursor-pointer hover:bg-gray-50"
              >
                <td className="px-4 py-3 font-medium">
                  {doc.original_filename ?? "Invoice"}
                </td>
                <td className="px-4 py-3">
                  <Badge label={doc.risk_level} tone={doc.risk_level} />
                </td>
                <td className="px-4 py-3 font-semibold">{doc.overall_risk_score}</td>
                <td className="px-4 py-3 text-gray-500">
                  {new Date(doc.created_at).toLocaleDateString("en-IN")}
                </td>
                <td className="px-4 py-3 text-gray-500">{timeAgo(doc.created_at)}</td>
              </tr>
            ))}
          </TBody>
        </Table>
      )}
    </PageWrapper>
  );
}
