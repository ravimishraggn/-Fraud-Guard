"use client";

import { APP_NAME, TEXT } from "@/lib/constants";
import { clearTokens } from "@/lib/auth";
import { classNames } from "@/lib/utils";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/dashboard", label: TEXT.nav.dashboard, icon: "📊" },
  { href: "/upload", label: TEXT.nav.upload, icon: "📤" },
  { href: "/review", label: TEXT.nav.review, icon: "🔍" },
  { href: "/vendors", label: TEXT.nav.vendors, icon: "🏢" },
  { href: "/rules", label: TEXT.nav.rules, icon: "⚙️" },
  { href: "/settings", label: TEXT.nav.settings, icon: "🛠️" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);

  const logout = () => {
    clearTokens();
    router.push("/login");
  };

  const nav = (
    <nav className="flex flex-1 flex-col gap-1 p-3">
      {NAV_ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          onClick={() => setMobileOpen(false)}
          className={classNames(
            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
            pathname.startsWith(item.href)
              ? "bg-accent text-white"
              : "text-gray-300 hover:bg-white/10 hover:text-white"
          )}
        >
          <span>{item.icon}</span>
          {item.label}
        </Link>
      ))}
      <button
        onClick={logout}
        className="mt-auto flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-gray-300 hover:bg-white/10 hover:text-white"
      >
        <span>🚪</span>
        {TEXT.common.logout}
      </button>
    </nav>
  );

  return (
    <>
      {/* Mobile top bar */}
      <div className="flex items-center justify-between bg-navy p-4 md:hidden">
        <span className="text-lg font-bold text-white">🛡️ {APP_NAME}</span>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="text-white"
          aria-label="Toggle menu"
        >
          ☰
        </button>
      </div>
      {mobileOpen && <div className="flex flex-col bg-navy md:hidden">{nav}</div>}

      {/* Desktop sidebar */}
      <aside className="hidden w-60 flex-col bg-navy md:flex">
        <div className="p-5 text-xl font-bold text-white">🛡️ {APP_NAME}</div>
        {nav}
      </aside>
    </>
  );
}
