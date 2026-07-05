"use client";

import { api } from "@/lib/api";
import { User } from "@/types";
import { useQuery } from "@tanstack/react-query";

export default function Header({ title }: { title: string }) {
  const { data: user } = useQuery<User>({
    queryKey: ["me"],
    queryFn: async () => (await api.get("/api/v1/auth/me")).data,
    staleTime: 5 * 60 * 1000,
  });

  return (
    <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
      <h1 className="text-xl font-semibold">{title}</h1>
      {user && (
        <div className="text-right">
          <p className="text-sm font-medium">{user.full_name}</p>
          <p className="text-xs uppercase text-gray-400">{user.role}</p>
        </div>
      )}
    </header>
  );
}
