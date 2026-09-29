"""STAGE 1 — EXTRACT: download gold H1 candles from MetaTrader 5.

EN: Connects to the MT5 terminal running on this Windows PC, finds the gold
    symbol (each broker names it differently) and saves OHLCV candles to CSV.
ES: Se conecta a la terminal MT5 abierta en este PC Windows, encuentra el
    símbolo del oro (cada broker lo llama distinto) y guarda las velas OHLCV en CSV.

Run / Ejecutar:
    python -m src.data.extract            # full history → data/raw/
    python -m src.data.extract --sample   # also refresh the small CI sample

NOTE: MetaTrader5 only works on Windows with the terminal open. CI and Docker
      never call this file; they use the data versioned by DVC (or the sample).
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from src.utils import get_logger, load_params, resolve

log = get_logger("extract")


def find_gold_symbol(mt5, candidates: list[str]) -> str:
    """Return the first candidate name that exists at this broker."""
    for name in candidates:
        info = mt5.symbol_info(name)
        if info is not None:
            mt5.symbol_select(name, True)  # make sure it's in Market Watch
            return name
    raise RuntimeError(f"No gold symbol found. Tried: {candidates}")


def fetch_rates(candidates: list[str], timeframe: str, n_bars: int) -> pd.DataFrame:
    import MetaTrader5 as mt5  # imported here: only exists on Windows

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()} — is the terminal open?")
    try:
        tf = getattr(mt5, f"TIMEFRAME_{timeframe}")
        symbol = find_gold_symbol(mt5, candidates)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No data returned for {symbol}: {mt5.last_error()}")
    finally:
        mt5.shutdown()

    df = pd.DataFrame(rates)
    # MT5 gives seconds since epoch in *broker server time*
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.rename(columns={"tick_volume": "volume"})
    df = df[["time", "open", "high", "low", "close", "volume", "spread"]]
    df.attrs["symbol"] = symbol
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", action="store_true", help="also write the small CI sample")
    args = parser.parse_args()

    p = load_params()["data"]
    df = fetch_rates(p["symbol_candidates"], p["timeframe"], p["n_bars"])

    # The last candle is still forming (not closed yet) → drop it
    # La última vela aún se está formando (no ha cerrado) → la quitamos
    df = df.iloc[:-1]

    out = resolve(p["raw_path"])
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    log.info("Symbol=%s | %d candles | %s → %s | saved %s",
             df.attrs.get("symbol"), len(df), df.time.min(), df.time.max(), out)

    if args.sample:
        sample = resolve(p["sample_path"])
        sample.parent.mkdir(parents=True, exist_ok=True)
        df.tail(p["sample_bars"]).to_csv(sample, index=False)
        log.info("CI sample: last %d candles → %s", p["sample_bars"], sample)


if __name__ == "__main__":
    sys.exit(main())
