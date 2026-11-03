"use client";

import React, { useState } from "react";
import { formatMW } from "@/lib/formatting/units";

export interface DiurnalPoint {
  interval_slot_number: number;
  start_time: string;
  end_time: string;
  tariff_time_block: string;
  weekday_avg_mw: number | string;
  weekend_avg_mw: number | string;
  weekday_min_mw?: number | string;
  weekday_max_mw?: number | string;
  weekend_min_mw?: number | string;
  weekend_max_mw?: number | string;
  weekday_weekend_spread_mw?: number | string;
}

interface DiurnalLoadCurveChartProps {
  data: DiurnalPoint[];
  title?: string;
  subtitle?: string;
  badge?: string;
}

export function DiurnalLoadCurveChart({
  data,
  title = "15-Minute Diurnal Load Profile",
  subtitle = "Average active power demand across 96 daily intervals · Weekday vs Weekend (MW)",
  badge = "PUCSL · Q05",
}: DiurnalLoadCurveChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return (
      <div className="card-glass p-6 text-center text-[#9AA5B0]">
        No diurnal data available.
      </div>
    );
  }

  const left = 65;
  const right = 32;
  const top = 30;
  const bottom = 48;
  const width = 850;
  const height = 340;
  const plotW = width - left - right;
  const plotH = height - top - bottom;

  const yMin = 1200;
  const yMax = 2800;

  const getX = (i: number) => left + (plotW / (data.length - 1)) * i;
  const getY = (val: number | string) => {
    const num = Number(val) || 0;
    return top + plotH - ((num - yMin) / (yMax - yMin)) * plotH;
  };

  const weekdayPath = data
    .map((d, i) => `${i === 0 ? "M" : "L"}${getX(i).toFixed(1)} ${getY(d.weekday_avg_mw).toFixed(1)}`)
    .join(" ");

  const weekendPath = data
    .map((d, i) => `${i === 0 ? "M" : "L"}${getX(i).toFixed(1)} ${getY(d.weekend_avg_mw).toFixed(1)}`)
    .join(" ");

  const yTicks = [1200, 1600, 2000, 2400, 2800];

  // Time markers every 4 hours (every 16 intervals)
  const timeMarkers = [
    { label: "00:00", idx: 0 },
    { label: "04:00", idx: 16 },
    { label: "08:00", idx: 32 },
    { label: "12:00", idx: 48 },
    { label: "16:00", idx: 64 },
    { label: "19:00 (Peak)", idx: 76 },
    { label: "23:45", idx: 95 },
  ];

  const activePoint = hoveredIdx !== null ? data[hoveredIdx] : null;

  return (
    <div className="card-glass p-6">
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

      <div className="relative pt-1 w-full">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto min-h-[290px] overflow-visible"
          role="img"
          aria-label="15-minute diurnal load curve graph"
        >
          {/* Shaded Evening Peak Window (18:30 to 22:30 -> interval 74 to 90) */}
          <rect
            x={getX(74)}
            y={top}
            width={getX(90) - getX(74)}
            height={plotH}
            fill="#FFF6E8"
            opacity="0.7"
          />
          <text
            x={(getX(74) + getX(90)) / 2}
            y={top + 16}
            textAnchor="middle"
            fill="#E9A43B"
            fontSize="10"
            fontWeight="700"
            letterSpacing="0.5px"
          >
            EVENING PEAK (18:30–22:30)
          </text>

          {/* Grid lines */}
          {yTicks.map((tick) => {
            const y = getY(tick);
            return (
              <g key={tick}>
                <line
                  x1={left}
                  y1={y}
                  x2={width - right}
                  y2={y}
                  stroke="#EDF0F3"
                  strokeWidth="1"
                />
                <text
                  x={left - 13}
                  y={y + 4}
                  textAnchor="end"
                  fill="#9BA6B1"
                  fontSize="12"
                  className="tabular-nums"
                >
                  {tick.toLocaleString()} MW
                </text>
              </g>
            );
          })}

          {/* Weekday line */}
          <path
            d={weekdayPath}
            fill="none"
            stroke="#19222D"
            strokeWidth="2.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Weekend line */}
          <path
            d={weekendPath}
            fill="none"
            stroke="#229C88"
            strokeWidth="2.4"
            strokeDasharray="4 3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Time markers */}
          {timeMarkers.map((marker) => {
            const x = getX(marker.idx);
            return (
              <g key={marker.idx}>
                <line
                  x1={x}
                  y1={top + plotH}
                  x2={x}
                  y2={top + plotH + 5}
                  stroke="#CBD5E1"
                  strokeWidth="1"
                />
                <text
                  x={x}
                  y={height - 14}
                  textAnchor="middle"
                  fill="#8693A1"
                  fontSize="11"
                  fontWeight="600"
                >
                  {marker.label}
                </text>
              </g>
            );
          })}

          {/* Hover interactive scrubber */}
          {data.map((d, i) => {
            const x = getX(i);
            return (
              <rect
                key={i}
                x={x - plotW / (data.length * 2)}
                y={top}
                width={plotW / data.length}
                height={plotH}
                fill="transparent"
                className="cursor-crosshair"
                onMouseEnter={() => setHoveredIdx(i)}
                onMouseLeave={() => setHoveredIdx(null)}
              />
            );
          })}

          {/* Active tooltip indicator */}
          {activePoint && hoveredIdx !== null && (
            <g>
              <line
                x1={getX(hoveredIdx)}
                y1={top}
                x2={getX(hoveredIdx)}
                y2={top + plotH}
                stroke="#A0AEC0"
                strokeWidth="1"
                strokeDasharray="3 3"
              />
              <circle
                cx={getX(hoveredIdx)}
                cy={getY(activePoint.weekday_avg_mw)}
                r="5"
                fill="#19222D"
              />
              <circle
                cx={getX(hoveredIdx)}
                cy={getY(activePoint.weekend_avg_mw)}
                r="5"
                fill="#229C88"
              />
            </g>
          )}
        </svg>
      </div>

      {/* Dynamic Hover Detail or Legend */}
      <div className="flex flex-wrap items-center justify-between gap-4 mt-3 text-[12px] pt-3 border-t border-[#EEF1F4]">
        <div className="flex items-center gap-6 text-[#6F7B8A]">
          <div className="flex items-center gap-2">
            <span className="w-3 h-0.5 bg-[#19222D]" />
            <span className="font-semibold text-[#19222D]">Weekday Avg MW</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-0.5 bg-[#229C88] border-b border-dashed border-[#229C88]" />
            <span className="font-semibold text-[#229C88]">Weekend Avg MW</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-[#FFF6E8] border border-[#E9A43B] rounded-sm" />
            <span className="text-[#86919E]">Evening Peak Window (18:30–22:30)</span>
          </div>
        </div>

        {activePoint ? (
          <div className="text-[12px] font-semibold text-[#19222D] bg-[#F8F9FB] px-3 py-1 rounded-md border border-[#E7EBF0]">
            Interval {activePoint.interval_slot_number} ({String(activePoint.start_time).slice(0, 5)}) · Weekday:{" "}
            <span className="text-[#19222D] font-bold">
              {formatMW(activePoint.weekday_avg_mw, 1)}
            </span>{" "}
            | Weekend:{" "}
            <span className="text-[#229C88] font-bold">
              {formatMW(activePoint.weekend_avg_mw, 1)}
            </span>
          </div>
        ) : (
          <div className="text-[11px] text-[#A1A9B4]">
            Hover across curve to inspect 15-minute interval demand
          </div>
        )}
      </div>
    </div>
  );
}
