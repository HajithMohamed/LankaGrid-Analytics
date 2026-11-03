"use client";

import React from "react";
import { Download, Printer } from "lucide-react";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  titleAccent?: string;
  description: string;
  children?: React.ReactNode;
  onExportCsv?: () => void;
  onPrint?: () => void;
  showPrint?: boolean;
}

export function PageHeader({
  eyebrow = "GridLens / National energy intelligence",
  title,
  titleAccent = ".",
  description,
  children,
  onExportCsv,
  onPrint,
  showPrint = true,
}: PageHeaderProps) {
  const handlePrint = () => {
    if (onPrint) {
      onPrint();
    } else {
      window.print();
    }
  };

  return (
    <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 mb-8">
      <div>
        <div className="text-[#229C88] text-[11px] font-extrabold tracking-[1.65px] uppercase mb-1">
          {eyebrow}
        </div>
        <h1 className="text-[32px] md:text-[40px] font-bold text-[#19222D] tracking-[-1.5px] leading-[1.15] m-0">
          {title}
          <span className="text-[#E9A43B]">{titleAccent}</span>
        </h1>
        <p className="text-[#748091] text-[14px] leading-relaxed max-w-3xl mt-2 mb-0">
          {description}
        </p>
      </div>

      <div className="flex items-center flex-wrap gap-2.5 lg:justify-end no-print">
        {children}

        {onExportCsv && (
          <button
            type="button"
            onClick={onExportCsv}
            className="h-[41px] px-3.5 rounded-[10px] bg-white border border-[#E2E7EE] hover:bg-[#F9FBFD] hover:border-[#CBD4DF] text-[#435166] text-[12px] font-semibold inline-flex items-center gap-2 transition-colors duration-150"
          >
            <Download size={15} />
            <span>Export CSV</span>
          </button>
        )}

        {showPrint && (
          <button
            type="button"
            onClick={handlePrint}
            className="h-[41px] px-4 rounded-[10px] bg-[#19222D] border border-[#19222D] hover:bg-[#303C4A] text-white text-[12px] font-semibold inline-flex items-center gap-2 transition-colors duration-150 shadow-sm"
          >
            <Printer size={15} />
            <span>Print Report</span>
          </button>
        )}
      </div>
    </div>
  );
}
