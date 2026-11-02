"use client";

import React from "react";

interface GenerationSourceShare {
  name: string;
  share: number;
  energyMWh: number;
  color: string;
}

const DEFAULT_MIX: GenerationSourceShare[] = [
  { name: "Coal", share: 42.56, energyMWh: 595524.50, color: "#343D49" },
  { name: "Fuel Oil", share: 27.69, energyMWh: 387450.75, color: "#E9A43B" },
  { name: "Major Hydro", share: 22.98, energyMWh: 321595.50, color: "#4278B9" },
  { name: "Other Renewables", share: 6.77, energyMWh: 94775.25, color: "#229C88" },
];

export function GenerationDonutChart({
  sources = DEFAULT_MIX,
  title = "Generation Mix",
  subtitle = "March 2024 · Share by source",
  badge = "PUCSL · Q01",
}: {
  sources?: GenerationSourceShare[];
  title?: string;
  subtitle?: string;
  badge?: string;
}) {
  // Build conic gradient string
  let currentPct = 0;
  const gradientStops = sources.map((s) => {
    const start = currentPct;
    currentPct += s.share;
    return `${s.color} ${start.toFixed(2)}% ${currentPct.toFixed(2)}%`;
  });
  const conicBg = `conic-gradient(${gradientStops.join(", ")})`;

  return (
    <div className="card-glass p-6 flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-[17px] font-bold text-[#19222D] tracking-[-0.45px] m-0">
              {title}
            </h2>
            <p className="text-[12px] text-[#86919E] mt-1 m-0">{subtitle}</p>
          </div>
          <span className="text-[11px] font-bold text-[#7D8896] px-2.5 py-1 border border-[#E7EBF0] rounded-[7px] bg-[#FAFBFC]">
            {badge}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 items-center gap-6 my-4 min-h-[220px]">
          {/* Donut ring */}
          <div className="relative w-[180px] h-[180px] mx-auto rounded-full flex items-center justify-center">
            <div
              className="absolute inset-0 rounded-full shadow-inner"
              style={{ background: conicBg }}
            />
            <div className="absolute inset-[24%] rounded-full bg-white flex flex-col items-center justify-center shadow-sm">
              <strong className="text-[22px] font-extrabold tracking-[-1px] text-[#19222D]">
                100%
              </strong>
              <span className="text-[10px] text-[#83909B] font-medium">
                Reported share
              </span>
            </div>
          </div>

          {/* Legend */}
          <div className="flex flex-col gap-3">
            {sources.map((s) => (
              <div
                key={s.name}
                className="grid grid-cols-[10px_1fr_auto] items-center gap-2.5 text-[12px]"
              >
                <span
                  className="w-[9px] h-[9px] rounded-[3px]"
                  style={{ backgroundColor: s.color }}
                />
                <span className="text-[#6E7A8A] font-medium">{s.name}</span>
                <span className="text-[#24313E] font-bold tabular-nums">
                  {s.share.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="p-3.5 border border-[#ECF0F4] rounded-[9px] bg-[#F8FAFB] text-[#687686] text-[11px] leading-relaxed mt-2">
        <strong className="text-[#42516A]">Period: </strong>
        March 2024 operational dispatch (744 hours). Lakvijaya Coal represents
        42.56% of total grid energy, followed by heavy fuel oil (27.69%) and
        major hydro (22.98%).
      </div>
    </div>
  );
}
