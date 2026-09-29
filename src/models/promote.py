"""STAGE 5 — EVALUATE & PROMOTE: the jury picks the champion.

EN: 1) Rank the candidate models by the primary metric on the unseen test set.
    2) QUALITY GATE: the best one must beat the "coin flip" baseline and a
       minimum ROC-AUC. If it fails, nothing is promoted.
    3) If it passes: register it in the MLflow Model Registry with the alias
       @champion and export a copy to models/champion/ (what the API serves).
ES: 1) Ordena los modelos candidatos por la métrica principal en el test no visto.
    2) CONTROL DE CALIDAD: el mejor debe vencer a la "moneda al aire" (baseline)
       y a un ROC-AUC mínimo. Si falla, no se promueve nada.
    3) Si pasa: se registra en el Model Registry de MLflow con el alias
       @champion y se exporta una copia a models/champion/ (lo que sirve la API).

Run / Ejecutar:
    python -m src.models.promote              # decide + register + export
    python -m src.models.promote --no-export  # decide only (used in CI smoke test)
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime

import mlflow
from mlflow import MlflowClient

from src.models.gate import gate
from src.models.tracking import setup_mlflow
from src.utils import get_logger, load_params, resolve, save_json

log = get_logger("promote")


def main() -> None:
    params = load_params()
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="reports/train_results.json")
    parser.add_argument("--no-export", action="store_true")
    args = parser.parse_args()

    with open(resolve(args.results), encoding="utf-8") as f:
        train_out = json.load(f)

    p = params["evaluate"]
    metric = f"test_{p['primary_metric']}"
    results = train_out["results"]
    baseline = next(r for r in results if r["model"] == "baseline")
    candidates = sorted([r for r in results if r["model"] != "baseline"],
                        key=lambda r: r[metric], reverse=True)
    best = candidates[0]

    log.info("Leaderboard (%s):", metric)
    for i, r in enumerate(sorted(results, key=lambda r: r[metric], reverse=True), 1):
        log.info("  %d. %-20s %s=%.4f  acc=%.4f", i, r["model"], metric, r[metric], r["test_accuracy"])

    checks = gate(best, baseline, p)
    passed = all(checks.values())
    for name, ok in checks.items():
        log.info("  %s %s", "✅" if ok else "❌", name)

    summary = {
        "decided_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "best_model": best["model"],
        "run_id": best["run_id"],
        "gate_passed": passed,
        "gate_checks": {k: bool(v) for k, v in checks.items()},
        "test_period": [train_out["test_start"], train_out["test_end"]],
        "best": {k: v for k, v in best.items() if k.startswith(("test_", "cv_"))},
        "baseline": {k: v for k, v in baseline.items() if k.startswith("test_")},
        "leaderboard": {r["model"]: round(r[metric], 4) for r in results},
    }
    save_json(summary, resolve(p["metrics_path"]))

    if not passed:
        log.warning("❌ Quality gate FAILED → no promotion. The current champion stays.")
        return
    if args.no_export:
        log.info("✅ Gate passed (--no-export: nothing registered)")
        return

    # ── Model Registry: give the winner a version number and the @champion alias ──
    setup_mlflow(params["train"]["experiment_name"])
    name = p["registered_model_name"]
    mv = mlflow.register_model(f"runs:/{best['run_id']}/model", name)
    client = MlflowClient()
    client.set_registered_model_alias(name, "champion", mv.version)
    client.set_model_version_tag(name, mv.version, "model_type", best["model"])
    log.info("🏆 Registered %s v%s → alias @champion", name, mv.version)

    # ── Export a self-contained copy for the API / Docker image ──
    out = resolve(p["champion_dir"])
    if out.exists():
        shutil.rmtree(out)
    local = mlflow.artifacts.download_artifacts(f"runs:/{best['run_id']}/model")
    shutil.copytree(local, out / "model")
    save_json({
        **summary,
        "registered_model": name,
        "version": int(mv.version),
        "features": train_out["features"],
        "feature_params": params["features"],
    }, out / "metadata.json")
    log.info("📦 Champion exported to %s", out)


if __name__ == "__main__":
    main()
