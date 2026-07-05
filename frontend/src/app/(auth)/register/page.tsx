"use client";

import Button from "@/components/ui/Button";
import { api } from "@/lib/api";
import { setTokens } from "@/lib/auth";
import { APP_NAME, TEXT } from "@/lib/constants";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    company_name: "",
    full_name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const update = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/api/v1/auth/register", form);
      setTokens(data.access_token, data.refresh_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail || TEXT.register.error);
    } finally {
      setLoading(false);
    }
  };

  const fields: { key: keyof typeof form; label: string; type: string }[] = [
    { key: "company_name", label: TEXT.register.companyLabel, type: "text" },
    { key: "full_name", label: TEXT.register.nameLabel, type: "text" },
    { key: "email", label: TEXT.register.emailLabel, type: "email" },
    { key: "password", label: TEXT.register.passwordLabel, type: "password" },
  ];

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-2xl font-bold">🛡️ {APP_NAME}</h1>
        <p className="mb-6 text-sm text-gray-500">{TEXT.register.title}</p>
        <form onSubmit={submit} className="space-y-4">
          {fields.map((f) => (
            <div key={f.key}>
              <label className="mb-1 block text-sm font-medium">{f.label}</label>
              <input
                type={f.type}
                required
                minLength={f.key === "password" ? 8 : 2}
                value={form[f.key]}
                onChange={update(f.key)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-accent focus:outline-none"
              />
            </div>
          ))}
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" loading={loading} className="w-full">
            {TEXT.register.submit}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-500">
          {TEXT.register.loginPrompt}{" "}
          <Link href="/login" className="font-medium text-accent hover:underline">
            {TEXT.register.loginLink}
          </Link>
        </p>
      </div>
    </div>
  );
}
