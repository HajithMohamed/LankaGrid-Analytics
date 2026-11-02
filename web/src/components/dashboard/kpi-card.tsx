import React from "react";

export interface KpiCardProps {
  name: string;
  value: string | number;
  unit?: string;
  period: string;
  sourcePill: string;
  accentColor: "#343D49" | "#E9A43B" | "#4278B9" | "#229C88" | "#D65F62" | string;
}

export function KpiCard({
  name,
  value,
  unit,
  period,
  sourcePill,
  accentColor,
}: KpiCardProps) {
  return (
    <div className="card-glass relative overflow-hidden p-[22px] min-h-[162px] flex flex-col justify-between">
      {/* Top accent grain */}
      <span
        className="top-grain-accent"
        style={{
          background: `linear-gradient(90deg, ${accentColor} 0 35%, transparent 35% 100%)`,
        }}
      />

      {/* Top row */}
      <div className="flex items-center justify-between gap-2.5">
        <span className="text-[12px] font-semibold text-[#768393]">{name}</span>
        <div className="w-[30px] h-[30px] rounded-[9px] bg-[#F8F9FB] border border-[#EEF1F4] flex items-center justify-center">
          <span
            className="w-2 h-2 rounded-full block"
            style={{ backgroundColor: accentColor }}
          />
        </div>
      </div>

      {/* Value */}
      <div className="text-[26px] md:text-[28px] font-extrabold text-[#19222D] tracking-[-1.25px] leading-tight my-4 tabular-nums">
        {value}
        {unit && (
          <span className="text-[13px] font-semibold text-[#7D8795] tracking-[-0.3px] ml-1.5">
            {unit}
          </span>
        )}
      </div>

      {/* Bottom row */}
      <div className="flex items-center justify-between text-[11px] text-[#9AA4AF]">
        <span>{period}</span>
        <span className="px-2.5 py-1 rounded-[6px] bg-[#F6F8FA] text-[#627184] text-[10px] font-bold uppercase tracking-wider">
          {sourcePill}
        </span>
      </div>
    </div>
  );
}
