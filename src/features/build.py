"""STAGE 3 — FEATURES: turn raw candles into "clues" + the answer (target).

EN: A model can't read a chart. We translate each candle into numbers
    ("clues") that describe what happened BEFORE it, plus the target:
        target = 1  if the NEXT candle closes higher  (price goes UP)
        target = 0  otherwise                         (price goes DOWN)
    Golden rule: a clue may only use information from the past.
    Using the future by accident is called DATA LEAKAGE.

ES: Un modelo no sabe leer un gráfico. Traducimos cada vela a números
    ("pistas") que describen lo que pasó ANTES, más el objetivo (target):
        target = 1  si la SIGUIENTE vela cierra más arriba (SUBE)
        target = 0  en otro caso                          (BAJA)
    Regla de oro: una pista solo puede usar información del pasado.
    Usar el futuro por accidente se llama DATA LEAKAGE (fuga de datos).

Run / Ejecutar:  python -m src.features.build [--input ...] [--output ...]
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from src.utils import get_logger, load_params, resolve

log = get_logger("features")


def rsi(close: pd.Series, window: int) -> pd.Series:
    """Relative Strength Index (0-100): >70 'overbought', <30 'oversold'."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def make_features(df: pd.DataFrame, p: dict, with_target: bool = True) -> pd.DataFrame:
    """Build the "clues" for every candle using only past/current information.

    with_target=True  → training   (adds the answer, drops the last candle: no future yet)
    with_target=False → prediction (API) — SAME code, so train == serve (no "skew")
    """
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])
    close = df["close"]
    ret = close.pct_change()

    out = pd.DataFrame({"time": df["time"], "close": close})

    # 1) Momentum: how much did price move in the last N hours?
    for lag in p["return_lags"]:
        out[f"ret_{lag}h"] = close.pct_change(lag)

    # 2) Trend: where is price vs. its moving averages? (>0 = above)
    for w in p["sma_windows"]:
        out[f"dist_sma_{w}"] = close / close.rolling(w).mean() - 1

    # 3) Oscillators
    out["rsi"] = rsi(close, p["rsi_window"])
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    out["macd_hist"] = (macd - macd.ewm(span=9, adjust=False).mean()) / close

    # 4) Risk: volatility and candle shape
    out["volatility"] = ret.rolling(p["volatility_window"]).std()
    out["range_pct"] = (df["high"] - df["low"]) / close
    out["body_pct"] = (df["close"] - df["open"]) / close
    vol_mean = df["volume"].rolling(24).mean()
    out["volume_z"] = (df["volume"] - vol_mean) / df["volume"].rolling(24).std()

    # 5) Calendar: gold behaves differently in Asia / London / New York hours
    out["hour_sin"] = np.sin(2 * np.pi * df["time"].dt.hour / 24)
    out["hour_cos"] = np.cos(2 * np.pi * df["time"].dt.hour / 24)
    out["dayofweek"] = df["time"].dt.dayofweek

    out = out.replace([np.inf, -np.inf], np.nan)
    feats = [c for c in out.columns if c not in ("time", "close")]
    if not with_target:
        return out.dropna(subset=feats).reset_index(drop=True)

    # 🎯 TARGET — the ONLY place where we look into the future (that's the answer!)
    # 🎯 OBJETIVO — el ÚNICO lugar donde miramos al futuro (¡es la respuesta!)
    future_close = close.shift(-p["horizon"])
    out["target"] = (future_close > close).astype(float)
    out.loc[future_close.isna(), "target"] = np.nan  # last candle has no answer yet
    out = out.dropna().reset_index(drop=True)
    out["target"] = out["target"].astype(int)
    return out


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in ("time", "close", "target")]


def main() -> None:
    params = load_params()
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=params["data"]["raw_path"])
    parser.add_argument("--output", default=params["features"]["processed_path"])
    args = parser.parse_args()

    raw = pd.read_csv(resolve(args.input))
    feats = make_features(raw, params["features"])

    out = resolve(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    feats.to_csv(out, index=False)
    log.info("%d rows x %d features | UP=%.1f%% DOWN=%.1f%% | saved %s",
             len(feats), len(feature_columns(feats)),
             feats.target.mean() * 100, (1 - feats.target.mean()) * 100, out)


if __name__ == "__main__":
    main()
