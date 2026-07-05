import Card from "@/components/ui/Card";

export default function KPICard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <Card>
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</p>
      <p className={`mt-2 text-2xl font-bold ${accent ?? "text-navy"}`}>{value}</p>
    </Card>
  );
}
