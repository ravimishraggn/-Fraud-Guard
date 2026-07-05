import { ReactNode } from "react";
import Header from "./Header";

export default function PageWrapper({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-1 flex-col">
      <Header title={title} />
      <main className="flex-1 p-4 md:p-6">{children}</main>
    </div>
  );
}
