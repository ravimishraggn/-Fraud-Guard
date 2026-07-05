"use client";

import PageWrapper from "@/components/layout/PageWrapper";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import { api } from "@/lib/api";
import { TEXT } from "@/lib/constants";
import { User } from "@/types";
import { useQuery } from "@tanstack/react-query";

export default function SettingsPage() {
  const { data: user, isLoading } = useQuery<User>({
    queryKey: ["me"],
    queryFn: async () => (await api.get("/api/v1/auth/me")).data,
  });

  return (
    <PageWrapper title={TEXT.settings.title}>
      {isLoading ? (
        <Spinner label={TEXT.common.loading} />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card title={TEXT.settings.team}>
            {user && (
              <div className="space-y-1">
                <p className="text-sm font-medium">{user.full_name}</p>
                <p className="text-sm text-gray-500">{user.email}</p>
                <p className="text-xs uppercase text-gray-400">{user.role}</p>
              </div>
            )}
            <p className="mt-4 text-xs text-gray-400">{TEXT.settings.comingSoon}</p>
          </Card>
          <Card title={TEXT.settings.notifications}>
            <p className="text-sm text-gray-500">
              Email alerts are sent to the account owner whenever an invoice needs review.
            </p>
          </Card>
          <Card title={TEXT.settings.limits}>
            <p className="text-sm text-gray-500">
              Starter plan — 100 documents per month. Contact sales to upgrade.
            </p>
          </Card>
        </div>
      )}
    </PageWrapper>
  );
}
