/**
 * Standardized Unit & Value Formatters for GridLens
 * Strictly adheres to Sri Lanka National Grid domain physics:
 * - Active Power: MW (rate / demand)
 * - Energy: MWh or GWh (integrated energy: 1 GWh = 1,000 MWh)
 * - Never mix MW and MWh!
 * - Safely handles strings from PostgreSQL pg driver (which returns NUMERIC as string)
 */

export function toNumeric(val: number | string | null | undefined): number | null {
  if (val === null || val === undefined || val === "") return null;
  const num = typeof val === "number" ? val : Number(val);
  return isNaN(num) ? null : num;
}

export function formatMW(val: number | string | null | undefined, decimals = 1): string {
  const num = toNumeric(val);
  if (num === null) return "—";
  return `${num.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} MW`;
}

export function formatMWh(val: number | string | null | undefined, decimals = 2): string {
  const num = toNumeric(val);
  if (num === null) return "—";
  return `${num.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} MWh`;
}

export function formatGWh(val: number | string | null | undefined, decimals = 2): string {
  const num = toNumeric(val);
  if (num === null) return "—";
  return `${num.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} GWh`;
}

export function formatNumber(val: number | string | null | undefined, decimals = 2): string {
  const num = toNumeric(val);
  if (num === null) return "—";
  return num.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function formatPercent(val: number | string | null | undefined, decimals = 1): string {
  const num = toNumeric(val);
  if (num === null) return "—";
  return `${num.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}%`;
}

export function formatCurrencyLKR(val: number | string | null | undefined): string {
  const num = toNumeric(val);
  if (num === null) return "—";
  return `LKR ${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatTimestamp(val: string | Date | null | undefined): string {
  if (!val) return "—";
  try {
    const d = new Date(val);
    return d.toLocaleString("en-US", {
      timeZone: "Asia/Colombo",
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return String(val);
  }
}
