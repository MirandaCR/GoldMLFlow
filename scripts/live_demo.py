"""LIVE DEMO — the whole loop in one command (great for showing someone!).

EN: 1) grabs the latest 300 closed H1 gold candles from your MT5 terminal
    2) sends them to the running API (local or Docker)
    3) prints the model's call for the NEXT hour
ES: 1) toma las últimas 300 velas H1 cerradas del oro desde tu terminal MT5
    2) las envía a la API en ejecución (local o Docker)
    3) muestra la predicción del modelo para la PRÓXIMA hora

Run / Ejecutar:
    uvicorn src.api.main:app          (or: docker compose up api)
    python scripts/live_demo.py [--url http://localhost:8000]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.extract import fetch_rates  # noqa: E402
from src.utils import load_params  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    p = load_params()["data"]
    df = fetch_rates(p["symbol_candidates"], p["timeframe"], 301).iloc[:-1]  # drop forming candle
    payload = {"candles": [
        {"time": r.time.isoformat(), "open": r.open, "high": r.high, "low": r.low,
         "close": r.close, "volume": float(r.volume)} for r in df.itertuples()]}

    info = httpx.get(f"{args.url}/model-info", timeout=10).json()
    pred = httpx.post(f"{args.url}/predict", json=payload, timeout=30).json()

    arrow = "🟢 ▲ UP / SUBE" if pred["direction"] == "UP" else "🔴 ▼ DOWN / BAJA"
    print(f"""
╔══════════════════════════════════════════════════╗
  🥇 GOLD H1 — next candle prediction
  Last closed candle : {pred['based_on_candle']}   close={df.close.iloc[-1]:.2f}
  Model              : {info['model']} v{info['version']}  (test AUC {info['metrics']['test_roc_auc']:.3f})
  Prediction         : {arrow}
  Probability UP     : {pred['prob_up']:.1%}
╚══════════════════════════════════════════════════╝
  ⚠️  Educational example — not financial advice.
""")


if __name__ == "__main__":
    main()
