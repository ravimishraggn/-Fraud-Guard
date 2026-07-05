"use client";

import PageWrapper from "@/components/layout/PageWrapper";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import Spinner from "@/components/ui/Spinner";
import { api } from "@/lib/api";
import { TEXT } from "@/lib/constants";
import { FraudRule } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

function RuleToggle({
  rule,
  onToggle,
  disabled,
}: {
  rule: FraudRule;
  onToggle: () => void;
  disabled: boolean;
}) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
        rule.is_active ? "bg-clean" : "bg-gray-300"
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          rule.is_active ? "translate-x-6" : "translate-x-1"
        }`}
      />
    </button>
  );
}

export default function RulesPage() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({
    rule_name: "",
    rule_type: "amount_limit",
    max_amount: "",
    max_invoices_per_month: "",
  });

  const { data, isLoading, isError } = useQuery<FraudRule[]>({
    queryKey: ["rules"],
    queryFn: async () => (await api.get("/api/v1/rules")).data,
  });

  const toggle = useMutation({
    mutationFn: async (rule: FraudRule) =>
      (await api.put(`/api/v1/rules/${rule.id}`, { is_active: !rule.is_active })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });

  const create = useMutation({
    mutationFn: async () => {
      const config: Record<string, unknown> = {};
      if (form.rule_type === "amount_limit" && form.max_amount) {
        config.max_amount = Number(form.max_amount);
      }
      if (form.rule_type === "frequency_limit" && form.max_invoices_per_month) {
        config.max_invoices_per_month = Number(form.max_invoices_per_month);
      }
      return (
        await api.post("/api/v1/rules", {
          rule_name: form.rule_name,
          rule_type: form.rule_type,
          config,
        })
      ).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      setModalOpen(false);
      setForm({ rule_name: "", rule_type: "amount_limit", max_amount: "", max_invoices_per_month: "" });
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };

  const builtins = (data ?? []).filter((r) => r.rule_type.startsWith("builtin_"));
  const customs = (data ?? []).filter((r) => !r.rule_type.startsWith("builtin_"));

  return (
    <PageWrapper title={TEXT.rules.title}>
      {isLoading && <Spinner label={TEXT.common.loading} />}
      {isError && (
        <Card>
          <p className="text-sm text-danger">{TEXT.common.error}</p>
        </Card>
      )}
      {data && (
        <div className="space-y-6">
          <Card title={TEXT.rules.defaultSection}>
            <p className="mb-3 text-xs text-gray-400">{TEXT.rules.builtinNote}</p>
            <ul className="divide-y divide-gray-100">
              {builtins.map((rule) => (
                <li key={rule.id} className="flex items-center justify-between gap-3 py-3">
                  <p className="text-sm font-medium">{rule.rule_name}</p>
                  <RuleToggle
                    rule={rule}
                    disabled={toggle.isPending}
                    onToggle={() => toggle.mutate(rule)}
                  />
                </li>
              ))}
            </ul>
          </Card>

          <Card title={TEXT.rules.customSection}>
            {customs.length > 0 && (
              <ul className="mb-4 divide-y divide-gray-100">
                {customs.map((rule) => (
                  <li key={rule.id} className="flex items-center justify-between gap-3 py-3">
                    <div>
                      <p className="text-sm font-medium">{rule.rule_name}</p>
                      <p className="text-xs text-gray-400">
                        {rule.rule_type}
                        {rule.config.max_amount ? ` — max ₹${rule.config.max_amount}` : ""}
                        {rule.config.max_invoices_per_month
                          ? ` — max ${rule.config.max_invoices_per_month}/month`
                          : ""}
                      </p>
                    </div>
                    <RuleToggle
                      rule={rule}
                      disabled={toggle.isPending}
                      onToggle={() => toggle.mutate(rule)}
                    />
                  </li>
                ))}
              </ul>
            )}
            <Button onClick={() => setModalOpen(true)}>+ {TEXT.rules.addCustom}</Button>
          </Card>
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={TEXT.rules.addCustom}>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">{TEXT.rules.form.name}</label>
            <input
              required
              value={form.rule_name}
              onChange={(e) => setForm({ ...form, rule_name: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">{TEXT.rules.form.type}</label>
            <select
              value={form.rule_type}
              onChange={(e) => setForm({ ...form, rule_type: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-accent focus:outline-none"
            >
              <option value="amount_limit">Amount limit</option>
              <option value="frequency_limit">Frequency limit</option>
              <option value="vendor_whitelist_only">Whitelisted vendors only</option>
              <option value="require_po">Require PO reference</option>
            </select>
          </div>
          {form.rule_type === "amount_limit" && (
            <div>
              <label className="mb-1 block text-sm font-medium">{TEXT.rules.form.maxAmount}</label>
              <input
                type="number"
                required
                min={1}
                value={form.max_amount}
                onChange={(e) => setForm({ ...form, max_amount: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-accent focus:outline-none"
              />
            </div>
          )}
          {form.rule_type === "frequency_limit" && (
            <div>
              <label className="mb-1 block text-sm font-medium">
                {TEXT.rules.form.maxPerMonth}
              </label>
              <input
                type="number"
                required
                min={1}
                value={form.max_invoices_per_month}
                onChange={(e) => setForm({ ...form, max_invoices_per_month: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-accent focus:outline-none"
              />
            </div>
          )}
          {create.isError && <p className="text-sm text-danger">{TEXT.common.error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              {TEXT.rules.form.cancel}
            </Button>
            <Button type="submit" loading={create.isPending}>
              {TEXT.rules.form.save}
            </Button>
          </div>
        </form>
      </Modal>
    </PageWrapper>
  );
}
