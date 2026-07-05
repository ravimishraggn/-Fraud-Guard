"use client";

import Button from "@/components/ui/Button";
import { api } from "@/lib/api";
import { setTokens } from "@/lib/auth";
import { APP_NAME, TEXT } from "@/lib/constants";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/api/v1/auth/login", { email, password });
      setTokens(data.access_token, data.refresh_token);
      router.push("/dashboard");
    } catch {
      setError(TEXT.login.error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-2xl font-bold">🛡️ {APP_NAME}</h1>
        <p className="mb-6 text-sm text-gray-500">{TEXT.login.title}</p>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">{TEXT.login.emailLabel}</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">{TEXT.login.passwordLabel}</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </div>
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" loading={loading} className="w-full">
            {TEXT.login.submit}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-500">
          {TEXT.login.registerPrompt}{" "}
          <Link href="/register" className="font-medium text-accent hover:underline">
            {TEXT.login.registerLink}
          </Link>
        </p>
      </div>
    </div>
  );
}
