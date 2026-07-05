"use client";

import Sidebar from "@/components/layout/Sidebar";
import { isLoggedIn } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import Spinner from "@/components/ui/Spinner";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) return <Spinner />;

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <div className="flex-1">{children}</div>
    </div>
  );
}
