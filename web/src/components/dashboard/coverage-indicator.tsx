import React from "react";

interface CoverageItem {
  title: string;
  source: string;
  period: string;
  factCount: string | number;
  unit?: string;
}

const DEFAULT_COVERAGE: CoverageItem[] = [
  {
    title: "Grid Dispatch Telemetry",
    source: "PUCSL Operational Log",
    period: "March 2024 (96 int/day)",
    factCount: "107,115",
    unit: "FACT ROWS",
  },
  {
    title: "Meteorological Observations",
    source: "NASA POWER API",
    period: "2020–2024 (Victoria & Mannar)",
    factCount: "21,924",
    unit: "FACT ROWS",
  },
  {
    title: "Electricity Billed Sales",
    source: "CEB Statistical Digest",
    period: "2020–2024 (Annual Audited)",
    factCount: "49",
    unit: "FACT ROWS",
  },
  {
    title: "Quarantined Anomalies",
    source: "ETL Validation Engine",
    period: "Dead-Letter Quarantine",
    factCount: "926",
    unit: "ISOLATED ROWS",
  },
];

export function CoverageIndicator({
  items = DEFAULT_COVERAGE,
  notice = "All metrics reflect official historical publications from CEB, PUCSL, and NASA POWER. The warehouse strictly isolates fact grains and enforces unit integrity (MW demand rate ≠ MWh integrated energy).",
}: {
  items?: CoverageItem[];
  notice?: string;
}) {
  return (
    <div className="card-glass p-6">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h3 className="text-[17px] font-bold text-[#19222D] tracking-[-0.45px] m-0">
            Warehouse Coverage
          </h3>
          <p className="text-[12px] text-[#86919E] mt-1 m-0">
            Verified data availability across historical partitions
          </p>
        </div>
        <span className="text-[11px] font-bold text-[#7D8896] px-2.5 py-1 border border-[#E7EBF0] rounded-[7px] whitespace-nowrap bg-[#FAFBFC]">
          Audited Facts
        </span>
      </div>

      <div className="divide-y divide-[#EEF1F4]">
        {items.map((item, idx) => (
          <div
            key={idx}
            className="flex items-center justify-between py-3.5 gap-3"
          >
            <div>
              <div className="text-[13px] font-bold text-[#19222D]">
                {item.title}
              </div>
              <p className="text-[11px] text-[#919DA8] m-0 mt-0.5">
                {item.source} · {item.period}
              </p>
            </div>
            <div className="text-right">
              <div className="text-[17px] font-bold text-[#19222D] tracking-[-0.6px] tabular-nums">
                {item.factCount}
              </div>
              <div className="text-[10px] font-semibold text-[#98A2AF] uppercase tracking-wider">
                {item.unit || "FACT ROWS"}
              </div>
            </div>
          </div>
        ))}
      </div>

      {notice && (
        <div className="mt-4 p-3.5 border border-[#ECF0F4] rounded-[9px] bg-[#F8FAFB] text-[#687686] text-[11px] leading-relaxed">
          <strong className="text-[#42516A]">Governance Note: </strong>
          {notice}
        </div>
      )}
    </div>
  );
}
