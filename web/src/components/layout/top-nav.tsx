"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X, Database } from "lucide-react";

interface TopNavProps {
  isLive?: boolean;
}

const NAV_LINKS = [
  { name: "Overview", href: "/" },
  { name: "Generation", href: "/generation" },
  { name: "Dispatch", href: "/dispatch" },
  { name: "Sales", href: "/sales" },
  { name: "Weather", href: "/weather" },
  { name: "Plants", href: "/plants" },
  { name: "Data Quality", href: "/data-quality" },
  { name: "Query Explorer", href: "/query-explorer" },
];

export function TopNav({ isLive = true }: TopNavProps) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 h-[76px] bg-white/95 backdrop-blur-md border-b border-[#E7EBF0]">
      <div className="max-w-[1500px] h-full mx-auto px-4 md:px-9 flex items-center justify-between gap-6 md:gap-10">
        {/* Brand */}
        <Link
          href="/"
          className="inline-flex items-center gap-2.5 text-[20px] font-extrabold tracking-[-0.8px] text-[#19222D] flex-shrink-0"
          aria-label="GridLens analytics home"
        >
          <span
            className="grid grid-cols-2 grid-rows-2 gap-[3px] -rotate-12 flex-shrink-0"
            aria-hidden="true"
          >
            <i className="w-[10px] h-[10px] rounded-[3px] bg-[#343D49] block" />
            <i className="w-[10px] h-[10px] rounded-[3px] bg-[#E9A43B] block" />
            <i className="w-[10px] h-[10px] rounded-[3px] bg-[#E9A43B] block" />
            <i className="w-[10px] h-[10px] rounded-[3px] bg-[#343D49] block" />
          </span>
          <span>GridLens</span>
          <span className="text-[#C0C8D1] font-normal">/</span>
          <span className="font-medium text-[12px] text-[#8D99A6] tracking-normal">
            intelligence
          </span>
        </Link>

        {/* Desktop Navigation */}
        <nav
          className="hidden xl:flex items-center gap-1 flex-1 h-full overflow-x-auto"
          aria-label="Main Navigation"
        >
          {NAV_LINKS.map((link) => {
            const isActive =
              link.href === "/"
                ? pathname === "/"
                : pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`whitespace-nowrap px-3 py-2 rounded-lg text-[13px] font-semibold transition-colors duration-150 ${
                  isActive
                    ? "bg-[#F2F4F7] text-[#19222D]"
                    : "text-[#738092] hover:bg-[#F5F7F9] hover:text-[#19222D]"
                }`}
              >
                {link.name}
              </Link>
            );
          })}
        </nav>

        {/* Right side status & mobile trigger */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2.5 text-[12px] text-[#697685] whitespace-nowrap bg-[#F8F9FB] border border-[#E7EBF0] px-3 py-1.5 rounded-full">
            <span
              className={`w-2 h-2 rounded-full ${
                isLive
                  ? "bg-[#229C88] ring-4 ring-[#E9F7F2]"
                  : "bg-[#E9A43B] ring-4 ring-[#FFF6E8]"
              }`}
            />
            <span className="font-medium">
              {isLive ? "PostgreSQL 18 Connected" : "Historical Snapshot"}
            </span>
          </div>

          <div
            className="w-[34px] h-[34px] rounded-full bg-[#EDF2F8] border border-[#E5EBF3] flex items-center justify-center text-[#374961] font-bold text-[11px]"
            title="University of Ruhuna, Faculty of Technology"
          >
            GL
          </div>

          {/* Mobile menu button */}
          <button
            type="button"
            className="xl:hidden p-2 rounded-lg text-[#738092] hover:bg-[#F2F4F7]"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="xl:hidden bg-white border-b border-[#E7EBF0] px-4 py-4 shadow-lg animate-in slide-in-from-top duration-200">
          <div className="flex flex-col gap-1">
            {NAV_LINKS.map((link) => {
              const isActive =
                link.href === "/"
                  ? pathname === "/"
                  : pathname === link.href || pathname.startsWith(`${link.href}/`);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2.5 rounded-lg text-[14px] font-semibold ${
                    isActive
                      ? "bg-[#F2F4F7] text-[#19222D]"
                      : "text-[#738092] hover:bg-[#F5F7F9]"
                  }`}
                >
                  {link.name}
                </Link>
              );
            })}
            <div className="pt-3 mt-2 border-t border-[#E7EBF0] flex items-center gap-2 text-xs text-[#697685]">
              <Database size={14} className="text-[#229C88]" />
              <span>Sri Lanka National Grid Analytics Warehouse</span>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
