"use client";

import React, { useState } from "react";

export interface BarDatum {
  label: string;
  value: number;
  formattedValue?: string;
  sublabel?: string;
  color?: string;
}

interface SimpleBarChartProps {
  data: BarDatum[];
  title: string;
  subtitle?: string;
  badge?: string;
  unit?: string;
  horizontal?: boolean;
}

export function SimpleBarChart({
  data,
  title,
  subtitle,
  badge,
  unit = "",
  horizontal = true,
}: SimpleBarChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return (
      <div className="card-glass p-6 text-center text-[#9AA5B0]">
        No chart data available.
      </div>
    );
  }

  const maxValue = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="card-glass p-6">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="text-[17px] font-bold text-[#19222D] tracking-[-0.45px] m-0">
            {title}
          </h2>
          {subtitle && (
            <p className="text-[12px] text-[#86919E] mt-1 m-0">{subtitle}</p>
          )}
        </div>
        {badge && (
          <span className="text-[11px] font-bold text-[#7D8896] px-2.5 py-1 border border-[#E7EBF0] rounded-[7px] bg-[#FAFBFC]">
            {badge}
          </span>
        )}
      </div>

      <div className="flex flex-col gap-3 my-2">
        {data.map((item, idx) => {
          const pct = Math.min(100, Math.max(0, (item.value / maxValue) * 100));
          const isHovered = hoveredIdx === idx;
          const barColor = item.color || "#4278B9";

          return (
            <div
              key={idx}
              className="group cursor-pointer"
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
            >
              <div className="flex items-baseline justify-between text-[12px] mb-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`font-medium transition-colors ${
                      isHovered ? "text-[#19222D] font-bold" : "text-[#465469]"
                    }`}
                  >
                    {item.label}
                  </span>
                  {item.sublabel && (
                    <span className="text-[10px] text-[#919DA8]">
                      ({item.sublabel})
                    </span>
                  )}
                </div>
                <span className="font-bold text-[#19222D] tabular-nums">
                  {item.formattedValue ||
                    `${item.value.toLocaleString("en-US", { maximumFractionDigits: 1 })} ${unit}`}
                </span>
              </div>

              {/* Progress track */}
              <div className="w-full h-2.5 bg-[#F0F3F7] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: barColor,
                    opacity: hoveredIdx !== null && !isHovered ? 0.6 : 1,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
