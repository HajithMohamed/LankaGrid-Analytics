"use client";

import React, { useState } from "react";

interface SalesDataPoint {
  year: number;
  total: number;
  productive: number;
  residential: number;
  share: number;
}

interface SalesTrendChartProps {
  data?: SalesDataPoint[];
  selectedYear?: string;
  onSelectYear?: (year: string) => void;
}

const DEFAULT_SALES: SalesDataPoint[] = [
  { year: 2020, total: 14287.0, productive: 7194.0, residential: 5090.0, share: 50.35 },
  { year: 2021, total: 15214.0, productive: 7939.0, residential: 5238.0, share: 52.18 },
  { year: 2022, total: 14520.0, productive: 7541.0, residential: 5044.0, share: 51.94 },
  { year: 2023, total: 14153.5, productive: 7731.5, residential: 4495.0, share: 54.63 },
  { year: 2024, total: 15190.5, productive: 8452.5, residential: 4701.0, share: 55.64 },
];

export function SalesTrendChart({
  data = DEFAULT_SALES,
  selectedYear = "all",
  onSelectYear,
}: SalesTrendChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const left = 65;
  const right = 32;
  const top = 25;
  const bottom = 48;
  const width = 800;
  const height = 315;
  const yMax = 18000;

  const plotW = width - left - right;
  const plotH = height - top - bottom;

  const getX = (i: number) => left + (plotW / (data.length - 1)) * i;
  const getY = (val: number) => top + plotH - (val / yMax) * plotH;

  const linePath = data
    .map((d, i) => `${i === 0 ? "M" : "L"}${getX(i).toFixed(1)} ${getY(d.total).toFixed(1)}`)
    .join(" ");

  const areaPath = `${linePath} L${getX(data.length - 1)} ${getY(0)} L${getX(0)} ${getY(0)} Z`;

  const yTicks = [0, 4500, 9000, 13500, 18000];

  return (
    <div className="card-glass p-6">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="text-[17px] font-bold text-[#19222D] tracking-[-0.45px] m-0">
            Electricity Sales Over Time
          </h2>
          <p className="text-[12px] text-[#86919E] mt-1 m-0">
            Audited annual billed electricity · 2020–2024 · GWh
          </p>
        </div>
        <span className="text-[11px] font-bold text-[#7D8896] px-2.5 py-1 border border-[#E7EBF0] rounded-[7px] bg-[#FAFBFC]">
          CEB Statistical Digests
        </span>
      </div>

      <div className="relative pt-1 w-full">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto min-h-[270px] overflow-visible"
          role="img"
          aria-label="Line graph of annual billed electricity sales from 2020 to 2024"
        >
          <defs>
            <linearGradient id="salesFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#E9A43B" stopOpacity="0.20" />
              <stop offset="100%" stopColor="#E9A43B" stopOpacity="0" />
            </linearGradient>
          </defs>

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
                  {tick === 0 ? "0" : `${tick / 1000}k`}
                </text>
              </g>
            );
          })}

          {/* Shaded Area */}
          <path d={areaPath} fill="url(#salesFill)" />

          {/* Stroke Line */}
          <path
            d={linePath}
            fill="none"
            stroke="#E9A43B"
            strokeWidth="3.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Points & Labels */}
          {data.map((d, i) => {
            const x = getX(i);
            const y = getY(d.total);
            const isSelected = selectedYear === String(d.year);
            const isHovered = hoveredIndex === i;
            const dim = selectedYear !== "all" && !isSelected;

            return (
              <g key={d.year}>
                {/* Year X Label */}
                <text
                  x={x}
                  y={height - 14}
                  textAnchor="middle"
                  fill={isSelected || isHovered ? "#19222D" : "#8693A1"}
                  fontSize="13"
                  fontWeight={isSelected || isHovered ? "750" : "500"}
                  className="cursor-pointer select-none"
                  onClick={() => onSelectYear && onSelectYear(String(d.year))}
                >
                  {d.year}
                </text>

                {/* Circle point */}
                <circle
                  cx={x}
                  cy={y}
                  r={isSelected ? 8 : isHovered ? 7 : 6}
                  fill="#FFFFFF"
                  stroke={dim ? "#D5DCE5" : "#E9A43B"}
                  strokeWidth={isSelected ? 4 : 3}
                  className="cursor-pointer transition-all duration-150"
                  onMouseEnter={() => setHoveredIndex(i)}
                  onMouseLeave={() => setHoveredIndex(null)}
                  onClick={() => onSelectYear && onSelectYear(String(d.year))}
                />

                {/* Hover/Selected Value Callout */}
                {(isSelected || isHovered) && (
                  <g>
                    <rect
                      x={x - 48}
                      y={y - 34}
                      width="96"
                      height="24"
                      rx="6"
                      fill="#19222D"
                    />
                    <text
                      x={x}
                      y={y - 18}
                      textAnchor="middle"
                      fill="#FFFFFF"
                      fontSize="11"
                      fontWeight="600"
                    >
                      {d.total.toLocaleString()} GWh
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="flex flex-wrap items-center gap-4 mt-3 text-[12px] text-[#6F7B8A]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#E9A43B]" />
          <span>Annual billed sales (GWh)</span>
        </div>
        <div className="ml-auto text-[11px] text-[#A1A9B4]">
          Click any year point to filter detailed sectoral tables
        </div>
      </div>
    </div>
  );
}
