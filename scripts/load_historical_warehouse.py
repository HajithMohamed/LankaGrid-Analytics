"""
Orchestrates Phase 2.2 Historical Data Expansion Warehouse Loading.
Loads into the primary development warehouse (sl_grid_warehouse):
1. CEB 5-Year Billed Electricity Sales (2020-2024)
2. NASA POWER 5-Year Meteorological Observations (2020-2024: 21,924 records)
3. PUCSL March 2024 Dispatch Curves
"""

import argparse
import time
from pathlib import Path

from src.common.config import DatabaseConfig
from src.etl.real_data_loader import RealDataWarehouseLoader


def main() -> None:
    parser = argparse.ArgumentParser(description="Load historical data into warehouse")
    parser.add_argument("--test-db", action="store_true", help="Target test database")
    args = parser.parse_args()

    config = DatabaseConfig.from_env(use_test_db=args.test_db)
    print(f"Connecting to warehouse '{config.dbname}' on port {config.port}...")
    loader = RealDataWarehouseLoader(config=config)

    # 1. Load CEB 5-Year Billed Electricity Sales
    print("\n--- 1. Loading CEB 5-Year Billed Electricity Sales (2020-2024) ---")
    t0 = time.time()
    ceb_results = loader.load_5yr_ceb_sales()
    print(f"Loaded {len(ceb_results)} annual CEB sales batches in {time.time() - t0:.2f}s:")
    for res in ceb_results:
        print(
            f"  Batch {res.batch_id} (Doc {res.source_document_id}): status={res.status}, inserted={res.rows_inserted}"
        )

    # 2. Load NASA POWER 5-Year Weather Dataset
    print("\n--- 2. Loading NASA POWER 5-Year Weather Dataset (2020-2024) ---")
    nasa_path = Path("data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json")
    if nasa_path.exists():
        t0 = time.time()
        nasa_res = loader.load_nasa_weather_json(nasa_path)
        print(
            f"Loaded NASA 5-Year weather in {time.time() - t0:.2f}s: status={nasa_res.status}, inserted={nasa_res.rows_inserted}, quarantined={nasa_res.rows_quarantined}"
        )

    # 3. Load PUCSL March 2024 Dispatch (Full 31-Day Coverage)
    print("\n--- 3. Loading PUCSL March 2024 Sub-Daily Dispatch Curves (All 31 Days) ---")
    pucsl_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
    if pucsl_path.exists():
        t0 = time.time()
        # Load all 31 daily sheets into partition fact_dispatch_interval_y2024
        dispatch_res = loader.load_pucsl_dispatch_xlsx(pucsl_path)
        print(
            f"Loaded PUCSL dispatch in {time.time() - t0:.2f}s: status={dispatch_res.status}, inserted={dispatch_res.rows_inserted}, updated={dispatch_res.rows_updated}, quarantined={dispatch_res.rows_quarantined}"
        )

    print("\nPrimary warehouse historical loading complete!")


if __name__ == "__main__":
    main()
