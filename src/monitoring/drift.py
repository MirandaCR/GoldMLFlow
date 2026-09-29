"""STAGE 6 — MONITOR: "is today's market still like the one we trained on?"

EN: Models learn patterns from a period of time. When the market changes
    (a crisis, new volatility regime...) those patterns may stop working.
    That's DATA DRIFT. We compare each clue's distribution in the training
    period vs. the most recent candles with a Kolmogorov-Smirnov test.
ES: Los modelos aprenden patrones de un periodo. Cuando el mercado cambia
    (una crisis, un nuevo régimen de volatilidad...) esos patrones pueden dejar
    de funcionar. Eso es DATA DRIFT. Comparamos la distribución de cada pista en
    el periodo de entrenamiento vs. las velas más recientes (prueba KS).

    Drift in many clues → time to retrain / Drift en muchas pistas → reentrenar

Run / Ejecutar:  python -m src.monitoring.drift [--input data/processed/features.csv]
"""
from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import ks_2samp  # noqa: E402

from src.features.build import feature_columns  # noqa: E402
from src.utils import get_logger, load_params, resolve, save_json  # noqa: E402

log = get_logger("drift")


def detect_drift(reference: pd.DataFrame, current: pd.DataFrame, features: list[str],
                 threshold: float) -> pd.DataFrame:
    rows = []
    for f in features:
        stat, p_value = ks_2samp(reference[f], current[f])
        rows.append({"feature": f, "ks_stat": stat, "p_value": p_value, "drift": p_value < threshold})
    return pd.DataFrame(rows).sort_values("ks_stat", ascending=False)


def main() -> None:
    params = load_params()
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=params["features"]["processed_path"])
    args = parser.parse_args()

    p = params["monitor"]
    df = pd.read_csv(resolve(args.input), parse_dates=["time"])
    feats = feature_columns(df)
    cut = int(len(df) * (1 - params["train"]["test_size"]))
    reference = df.iloc[:cut]                 # what the model learned from
    current = df.iloc[-p["recent_bars"]:]     # the market "today"

    report = detect_drift(reference, current, feats, p["p_value_threshold"])
    share = float(report["drift"].mean())
    for _, r in report.iterrows():
        log.info("%s %-14s KS=%.3f p=%.4f", "⚠️ " if r.drift else "✅", r.feature, r.ks_stat, r.p_value)
    log.info("Drifted features: %.0f%% → %s", share * 100,
             "consider retraining / considera reentrenar" if share > 0.3 else "OK")

    save_json({"reference_period": [str(reference.time.min()), str(reference.time.max())],
               "current_period": [str(current.time.min()), str(current.time.max())],
               "drift_share": share, "retrain_recommended": share > 0.3,
               "features": report.to_dict(orient="records")}, resolve(p["report_path"]))

    # Visual: reference vs current for the 4 most drifted clues
    top = report.head(4)["feature"].tolist()
    fig, axes = plt.subplots(1, len(top), figsize=(4 * len(top), 3))
    for ax, f in zip(axes, top, strict=True):
        ax.hist(reference[f], bins=50, density=True, alpha=0.5, label="train period", color="#999")
        ax.hist(current[f], bins=50, density=True, alpha=0.6, label="recent", color="#e76f51")
        ax.set_title(f)
    axes[0].legend()
    fig.suptitle("Data drift: training vs recent market / entrenamiento vs mercado reciente")
    fig.tight_layout()
    out = resolve("reports/figures/drift.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
