"""STAGE 2 — VALIDATE: "is the data healthy?" before any model sees it.

EN: Garbage in → garbage out. These checks stop the pipeline if the raw data
    is broken (missing values, duplicated hours, impossible candles...).
ES: Basura entra → basura sale. Estas revisiones detienen el pipeline si los
    datos crudos están rotos (vacíos, horas duplicadas, velas imposibles...).

Run / Ejecutar:  python -m src.data.validate [--input data/sample/xauusd_h1_sample.csv]
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from src.utils import get_logger, load_params, resolve, save_json

log = get_logger("validate")

REQUIRED_COLUMNS = ["time", "open", "high", "low", "close", "volume"]


def run_checks(df: pd.DataFrame, min_rows: int, max_missing_pct: float) -> dict[str, bool]:
    """Each check returns True when OK. / Cada revisión devuelve True si está OK."""
    has_cols = all(c in df.columns for c in REQUIRED_COLUMNS)
    if not has_cols:
        return {"required_columns": False}
    t = pd.to_datetime(df["time"])
    return {
        "required_columns": True,
        "enough_rows": len(df) >= min_rows,
        "no_missing_values": df[REQUIRED_COLUMNS].isna().mean().max() * 100 <= max_missing_pct,
        "no_duplicated_timestamps": not t.duplicated().any(),
        "time_is_sorted": t.is_monotonic_increasing,
        "prices_positive": (df[["open", "high", "low", "close"]] > 0).all().all(),
        "high_is_highest": (df["high"] >= df[["open", "close", "low"]].max(axis=1)).all(),
        "low_is_lowest": (df["low"] <= df[["open", "close", "high"]].min(axis=1)).all(),
    }


def main() -> int:
    params = load_params()
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=params["data"]["raw_path"])
    args = parser.parse_args()

    p = params["validate"]
    df = pd.read_csv(resolve(args.input))
    checks = run_checks(df, p["min_rows"], p["max_missing_pct"])
    checks = {k: bool(v) for k, v in checks.items()}

    for name, ok in checks.items():
        log.info("%s %s", "✅" if ok else "❌", name)

    report = {"input": args.input, "rows": len(df), "passed": all(checks.values()), "checks": checks}
    save_json(report, resolve(p["report_path"]))

    if not report["passed"]:
        log.error("Data validation FAILED → pipeline stopped / validación FALLÓ → pipeline detenido")
        return 1
    log.info("Data validation passed (%d rows)", len(df))
    return 0


if __name__ == "__main__":
    sys.exit(main())
