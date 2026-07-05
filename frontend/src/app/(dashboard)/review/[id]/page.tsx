"use client";

import PageWrapper from "@/components/layout/PageWrapper";
import DecisionButtons from "@/components/review/DecisionButtons";
import ExtractedFields from "@/components/review/ExtractedFields";
import FraudFlagCard from "@/components/review/FraudFlagCard";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import { api } from "@/lib/api";
import { TEXT } from "@/lib/constants";
import { Document, ExtractedField, FraudFlag } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const doc = useQuery<Document>({
    queryKey: ["document", id],
    queryFn: async () => (await api.get(`/api/v1/documents/${id}`)).data,
  });
  const fields = useQuery<ExtractedField[]>({
    queryKey: ["document", id, "fields"],
    queryFn: async () => (await api.get(`/api/v1/documents/${id}/fields`)).data,
  });
  const flags = useQuery<FraudFlag[]>({
    queryKey: ["document", id, "flags"],
    queryFn: async () => (await api.get(`/api/v1/documents/${id}/flags`)).data,
  });
  const fileUrl = useQuery<{ url: string }>({
    queryKey: ["document", id, "file-url"],
    queryFn: async () => (await api.get(`/api/v1/documents/${id}/file-url`)).data,
    retry: false,
  });

  const review = useMutation({
    mutationFn: async ({ decision, note }: { decision: string; note: string }) =>
      (await api.post(`/api/v1/documents/${id}/review`, { decision, note: note || null })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document", id] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
      router.push("/review");
    },
  });

  if (doc.isLoading) {
    return (
      <PageWrapper title={TEXT.review.title}>
        <Spinner label={TEXT.common.loading} />
      </PageWrapper>
    );
  }
  if (doc.isError || !doc.data) {
    return (
      <PageWrapper title={TEXT.review.title}>
        <Card>
          <p className="text-sm text-danger">{TEXT.common.error}</p>
        </Card>
      </PageWrapper>
    );
  }

  const d = doc.data;
  const isImage = d.mime_type?.startsWith("image/");

  return (
    <PageWrapper title={d.original_filename ?? "Invoice"}>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Badge label={d.risk_level} tone={d.risk_level} />
        <span className="text-sm text-gray-500">
          Risk score: <strong>{d.overall_risk_score}/100</strong>
        </span>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium uppercase text-gray-500">
          {d.status.replace(/_/g, " ")}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        {/* Left — document preview */}
        <Card className="lg:col-span-3">
          {fileUrl.data?.url ? (
            isImage ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={fileUrl.data.url}
                alt={d.original_filename ?? "Invoice"}
                className="mx-auto max-h-[75vh] rounded-lg"
              />
            ) : (
              <object
                data={fileUrl.data.url}
                type="application/pdf"
                className="h-[75vh] w-full rounded-lg"
              >
                <p className="p-4 text-sm text-gray-500">{TEXT.detail.previewUnavailable}</p>
              </object>
            )
          ) : (
            <p className="p-4 text-sm text-gray-500">{TEXT.detail.previewUnavailable}</p>
          )}
        </Card>

        {/* Right — fields, flags, decision */}
        <div className="space-y-4 lg:col-span-2">
          <Card title={TEXT.detail.extractedFields}>
            {fields.isLoading ? <Spinner /> : <ExtractedFields fields={fields.data ?? []} />}
          </Card>

          <Card title={TEXT.detail.fraudFlags}>
            {flags.isLoading ? (
              <Spinner />
            ) : (flags.data ?? []).length === 0 ? (
              <p className="text-sm text-gray-500">✅ {TEXT.detail.noFlags}</p>
            ) : (
              <div className="space-y-3">
                {(flags.data ?? []).map((flag) => (
                  <FraudFlagCard key={flag.id} flag={flag} />
                ))}
              </div>
            )}
          </Card>

          <Card>
            <DecisionButtons
              submitting={review.isPending}
              onDecision={(decision, note) => review.mutate({ decision, note })}
            />
            {review.isError && (
              <p className="mt-2 text-sm text-danger">{TEXT.common.error}</p>
            )}
          </Card>
        </div>
      </div>
    </PageWrapper>
  );
}
