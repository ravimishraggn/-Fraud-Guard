"use client";

import PageWrapper from "@/components/layout/PageWrapper";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import { Table, TBody, THead } from "@/components/ui/Table";
import { api } from "@/lib/api";
import { TEXT } from "@/lib/constants";
import { formatPaise } from "@/lib/utils";
import { Vendor } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

function riskTone(score: number): string {
  if (score >= 60) return "high";
  if (score >= 30) return "medium";
  if (score > 0) return "low";
  return "clean";
}

export default function VendorsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery<Vendor[]>({
    queryKey: ["vendors"],
    queryFn: async () => (await api.get("/api/v1/vendors")).data,
  });

  const toggle = useMutation({
    mutationFn: async (vendorId: string) =>
      (await api.post(`/api/v1/vendors/${vendorId}/whitelist`)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vendors"] }),
  });

  return (
    <PageWrapper title={TEXT.vendors.title}>
      {isLoading && <Spinner label={TEXT.common.loading} />}
      {isError && (
        <Card>
          <p className="text-sm text-danger">{TEXT.common.error}</p>
        </Card>
      )}
      {data && data.length === 0 && (
        <Card>
          <p className="py-8 text-center text-sm text-gray-500">{TEXT.vendors.empty}</p>
        </Card>
      )}
      {data && data.length > 0 && (
        <Table>
          <THead
            headers={["Name", "GSTIN", "Invoices", "Total amount", "Flagged", "Risk", "Whitelist"]}
          />
          <TBody>
            {data.map((vendor) => (
              <tr key={vendor.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{vendor.name}</td>
                <td className="px-4 py-3 font-mono text-xs text-gray-500">
                  {vendor.gstin ?? "—"}
                </td>
                <td className="px-4 py-3">{vendor.total_invoices}</td>
                <td className="px-4 py-3">{formatPaise(vendor.total_amount_paise)}</td>
                <td className="px-4 py-3">
                  {vendor.flagged_count > 0 ? (
                    <span className="font-semibold text-danger">{vendor.flagged_count}</span>
                  ) : (
                    0
                  )}
                </td>
                <td className="px-4 py-3">
                  <Badge label={String(vendor.risk_score)} tone={riskTone(vendor.risk_score)} />
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggle.mutate(vendor.id)}
                    disabled={toggle.isPending}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      vendor.is_whitelisted ? "bg-clean" : "bg-gray-300"
                    }`}
                    title={
                      vendor.is_whitelisted
                        ? TEXT.vendors.whitelisted
                        : TEXT.vendors.notWhitelisted
                    }
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        vendor.is_whitelisted ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                </td>
              </tr>
            ))}
          </TBody>
        </Table>
      )}
    </PageWrapper>
  );
}
