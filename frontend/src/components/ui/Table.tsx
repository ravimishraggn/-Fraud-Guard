import { ReactNode } from "react";

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">{children}</table>
    </div>
  );
}

export function THead({ headers }: { headers: string[] }) {
  return (
    <thead className="bg-gray-50">
      <tr>
        {headers.map((h) => (
          <th
            key={h}
            className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500"
          >
            {h}
          </th>
        ))}
      </tr>
    </thead>
  );
}

export function TBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-gray-100">{children}</tbody>;
}
