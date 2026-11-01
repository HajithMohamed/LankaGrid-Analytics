"""
Phase 3 Analytical Visualizations & Charts Generator.
Generates publication-quality charts from genuine PostgreSQL query outputs.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_all_charts() -> None:
    output_dir = Path("results/phase3/query-outputs")
    charts_dir = Path("results/phase3/charts")
    charts_dir.mkdir(parents=True, exist_ok=True)

    # Style configuration
    plt.rcParams.update({
        "font.sans-serif": "DejaVu Sans",
        "axes.edgecolor": "#cccccc",
        "axes.linewidth": 0.8,
        "grid.color": "#eeeeee",
        "grid.linestyle": "--",
        "grid.linewidth": 0.5,
    })

    # =========================================================================
    # Chart 1: Generation Mix by Technology (Q01)
    # =========================================================================
    q01_path = output_dir / "Q01.csv"
    if q01_path.exists():
        labels, values, colors = [], [], []
        color_map = {
            "THERMAL_COAL": "#4a5568",
            "THERMAL_OIL": "#dd6b20",
            "MAJOR_HYDRO": "#3182ce",
            "MINI_HYDRO": "#63b3ed",
            "SOLAR_UTILITY": "#ecc94b",
            "WIND": "#38a169",
            "BIOMASS": "#9f7aea",
        }
        with open(q01_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["grp_src"] == "0" and row["grp_cat"] == "0":
                    src = row["energy_source_code"]
                    val = float(row["total_generation_mwh"])
                    labels.append(src.replace("_", " "))
                    values.append(val)
                    colors.append(color_map.get(src, "#a0aec0"))

        fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
        bars = ax.barh(labels, [v / 1000.0 for v in values], color=colors, edgecolor="#2d3748", height=0.6)
        ax.set_xlabel("Total Generation in March 2024 (GWh)", fontsize=11, fontweight="bold")
        ax.set_title("GridLens — National Generation Mix by Technology (March 2024)\nSource: PUCSL 15-Minute Operational Dispatch Telemetry (107,115 Facts)", fontsize=12, pad=15)
        ax.grid(True, axis="x")
        for bar in bars:
            w = bar.get_width()
            pct = (w / (sum(values) / 1000.0)) * 100.0
            ax.text(w + 10, bar.get_y() + bar.get_height() / 2, f"{w:.1f} GWh ({pct:.1f}%)", va="center", fontsize=9, fontweight="bold")
        ax.set_xlim(0, max([v / 1000.0 for v in values]) * 1.25)
        plt.tight_layout()
        chart1_path = charts_dir / "chart_01_generation_mix_march_2024.png"
        fig.savefig(chart1_path)
        plt.close(fig)
        print(f"Generated {chart1_path.name}")

    # =========================================================================
    # Chart 2: Daily Renewable vs Non-Renewable Dispatch (Q02)
    # =========================================================================
    q02_path = output_dir / "Q02.csv"
    if q02_path.exists():
        days, ren_shares, ren_7d = [], [], []
        with open(q02_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                day_num = int(row["calendar_date"].split("-")[2])
                days.append(day_num)
                ren_shares.append(float(row["renewable_share_pct"]))
                ren_7d.append(float(row["renewable_share_7d_ma_pct"]))

        fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
        ax.bar(days, ren_shares, color="#68d391", alpha=0.6, label="Daily Renewable Share (%)", edgecolor="#38a169", width=0.7)
        ax.plot(days, ren_7d, color="#22543d", linewidth=2.5, label="7-Day Centered Moving Average (%)")
        ax.axhline(70.0, color="#e53e3e", linestyle="--", linewidth=1.5, label="Statutory 2030 Renewable Target (70%)")
        ax.set_xlabel("Day of Month (March 2024)", fontsize=11, fontweight="bold")
        ax.set_ylabel("Renewable Generation Share (%)", fontsize=11, fontweight="bold")
        ax.set_title("GridLens — Daily Renewable Penetration Share (March 2024)\nTracking Pre-Monsoon Dry Season Generation Dynamics", fontsize=12, pad=15)
        ax.set_ylim(0, 100)
        ax.set_xticks(range(1, 32, 2))
        ax.legend(loc="upper right", framealpha=0.9)
        ax.grid(True)
        plt.tight_layout()
        chart2_path = charts_dir / "chart_02_renewable_daily_share_march_2024.png"
        fig.savefig(chart2_path)
        plt.close(fig)
        print(f"Generated {chart2_path.name}")

    # =========================================================================
    # Chart 3: 15-Minute Load Curve: Weekday vs Weekend (Q05)
    # =========================================================================
    q05_path = output_dir / "Q05.csv"
    if q05_path.exists():
        slots, weekday_mw, weekend_mw = [], [], []
        with open(q05_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                slots.append(int(row["interval_slot_number"]))
                weekday_mw.append(float(row["weekday_avg_mw"]))
                weekend_mw.append(float(row["weekend_avg_mw"]))

        fig, ax = plt.subplots(figsize=(11, 5.5), dpi=300)
        time_hours = [s * 0.25 for s in slots]
        ax.plot(time_hours, weekday_mw, color="#2b6cb0", linewidth=2.5, label="Weekday Average (21 Days)")
        ax.plot(time_hours, weekend_mw, color="#dd6b20", linewidth=2.2, linestyle="--", label="Weekend Average (10 Days)")
        ax.fill_between(time_hours, weekday_mw, weekend_mw, color="#bee3f8", alpha=0.5, label="Industrial / Commercial Demand Drop")
        ax.set_xlabel("Time of Day (SLST, Hours)", fontsize=11, fontweight="bold")
        ax.set_ylabel("Dispatched Active Power (MW)", fontsize=11, fontweight="bold")
        ax.set_title("GridLens — 15-Minute Daily Dispatch Curves (March 2024)\nWeekday vs Weekend Load Profile Comparison (107,115 Facts)", fontsize=12, pad=15)
        ax.set_xticks(range(0, 25, 2))
        ax.set_xlim(0, 24)
        ax.legend(loc="lower right", framealpha=0.9)
        ax.grid(True)
        plt.tight_layout()
        chart3_path = charts_dir / "chart_03_dispatch_curve_weekday_vs_weekend.png"
        fig.savefig(chart3_path)
        plt.close(fig)
        print(f"Generated {chart3_path.name}")

    # =========================================================================
    # Chart 4: Five-Year Sectoral Electricity Sales Trends (Q09)
    # =========================================================================
    q09_path = output_dir / "Q09.csv"
    if q09_path.exists():
        sector_series: dict[str, dict[int, float]] = {}
        with open(q09_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sec = row["sector_code"]
                yr = int(row["calendar_year"])
                gwh = float(row["energy_sold_gwh"])
                if sec not in sector_series:
                    sector_series[sec] = {}
                sector_series[sec][yr] = gwh

        years = [2020, 2021, 2022, 2023, 2024]
        fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
        display_sectors = [
            ("DOMESTIC", "Domestic (Residential)", "#e53e3e", "-"),
            ("INDUSTRIAL", "Industrial", "#3182ce", "-"),
            ("GENERAL_PURPOSE", "General Purpose (Commercial)", "#38a169", "-"),
            ("BULK_LECO", "Bulk Supply to LECO", "#805ad5", "--"),
            ("HOTEL", "Hotel & Tourism", "#dd6b20", "-."),
        ]
        for sec_code, label, color, style in display_sectors:
            if sec_code in sector_series:
                y_vals = [sector_series[sec_code].get(yr, 0) for yr in years]
                ax.plot(years, y_vals, marker="o", label=label, color=color, linestyle=style, linewidth=2)

        ax.set_xlabel("Calendar Year", fontsize=11, fontweight="bold")
        ax.set_ylabel("Billed Electricity Sales (GWh)", fontsize=11, fontweight="bold")
        ax.set_title("GridLens — Five-Year Sectoral Electricity Sales Trajectories (2020-2024)\nSource: CEB Audited Statistical Digests (Audited Billing Records)", fontsize=12, pad=15)
        ax.set_xticks(years)
        ax.legend(loc="upper left", framealpha=0.9)
        ax.grid(True)
        plt.tight_layout()
        chart4_path = charts_dir / "chart_04_five_year_sales_trends.png"
        fig.savefig(chart4_path)
        plt.close(fig)
        print(f"Generated {chart4_path.name}")

    # =========================================================================
    # Chart 5: Five-Year Solar Irradiance: Victoria vs Mannar (Q13)
    # =========================================================================
    q13_path = output_dir / "Q13.csv"
    if q13_path.exists():
        years = [2020, 2021, 2022, 2023, 2024]
        mannar_psh, victoria_psh = [], []
        with open(q13_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                loc = row["location_code"]
                psh = float(row["approx_peak_sun_hours_psh"])
                if loc == "LOC_MANNAR_WIND":
                    mannar_psh.append(psh)
                elif loc == "LOC_VICTORIA_CATCHMENT":
                    victoria_psh.append(psh)

        fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
        import numpy as np
        x = np.arange(len(years))
        width = 0.35
        ax.bar(x - width / 2, mannar_psh, width, label="Mannar Island (Northern Dry Zone)", color="#ecc94b", edgecolor="#b7791f")
        ax.bar(x + width / 2, victoria_psh, width, label="Victoria Hydro Basin (Central Highlands)", color="#4299e1", edgecolor="#2b6cb0")
        ax.set_xlabel("Calendar Year", fontsize=11, fontweight="bold")
        ax.set_ylabel("Peak Sun Hours (PSH = kWh/m2/day)", fontsize=11, fontweight="bold")
        ax.set_title("GridLens — Annual Solar Resource Comparison: Victoria vs Mannar (2020-2024)\nNASA POWER Meteorological Database (1,827 Days, LST Standard)", fontsize=12, pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels([str(y) for y in years])
        ax.set_ylim(0, 7.0)
        ax.legend(loc="lower right", framealpha=0.9)
        ax.grid(True, axis="y")
        plt.tight_layout()
        chart5_path = charts_dir / "chart_05_solar_irradiance_victoria_vs_mannar.png"
        fig.savefig(chart5_path)
        plt.close(fig)
        print(f"Generated {chart5_path.name}")

    # =========================================================================
    # Chart 6: Evening Peak vs Daytime Technology Contribution (Q04 / Q20)
    # =========================================================================
    q04_path = output_dir / "Q04.csv"
    if q04_path.exists():
        technologies, day_shares, peak_shares = [], [], []
        with open(q04_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                technologies.append(row["energy_category"])
                day_shares.append(float(row["day_share_pct"]))
                peak_shares.append(float(row["peak_share_pct"]))

        fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
        import numpy as np
        x = np.arange(len(technologies))
        width = 0.35
        ax.bar(x - width / 2, day_shares, width, label="Daytime Share (05:30 - 18:30)", color="#f6ad55", edgecolor="#c05621")
        ax.bar(x + width / 2, peak_shares, width, label="Evening Peak Share (18:30 - 22:30)", color="#4a5568", edgecolor="#1a202c")
        ax.set_xlabel("Energy Technology Category", fontsize=11, fontweight="bold")
        ax.set_ylabel("Contribution Share (%)", fontsize=11, fontweight="bold")
        ax.set_title("GridLens — Technology Contribution: Daytime vs Evening Peak (March 2024)\nDemonstrates Peaking Hydro Ramping and Solar Curtailment at Night", fontsize=12, pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(technologies, rotation=15, ha="right")
        ax.set_ylim(0, 55)
        ax.legend(loc="upper right", framealpha=0.9)
        ax.grid(True, axis="y")
        plt.tight_layout()
        chart6_path = charts_dir / "chart_06_tou_generation_contribution.png"
        fig.savefig(chart6_path)
        plt.close(fig)
        print(f"Generated {chart6_path.name}")

    print("All Phase 3 charts generated successfully in results/phase3/charts/.")


if __name__ == "__main__":
    generate_all_charts()

