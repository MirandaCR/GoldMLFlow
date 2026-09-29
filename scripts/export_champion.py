"""ROLLBACK helper — export whatever version @champion points to into models/champion/.

EN: 1) In the MLflow UI (Models → gold-direction-h1) move the @champion alias to any version
    2) python scripts/export_champion.py
    3) git commit models/champion → CI checks it → CD publishes that model
ES: 1) En la interfaz de MLflow (Models → gold-direction-h1) mueve el alias @champion a otra versión
    2) python scripts/export_champion.py
    3) git commit models/champion → el CI lo revisa → el CD publica ese modelo
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mlflow  # noqa: E402
from mlflow import MlflowClient  # noqa: E402

from src.models.tracking import setup_mlflow  # noqa: E402
from src.utils import get_logger, load_params, resolve, save_json  # noqa: E402

log = get_logger("export_champion")


def main() -> None:
    params = load_params()
    p = params["evaluate"]
    setup_mlflow(params["train"]["experiment_name"])
    client = MlflowClient()
    mv = client.get_model_version_by_alias(p["registered_model_name"], "champion")
    run = client.get_run(mv.run_id)
    m = run.data.metrics

    # Baseline metrics come from the sibling "baseline" run of the same training session
    parent = run.data.tags.get("mlflow.parentRunId")
    sib = mlflow.search_runs(experiment_ids=[run.info.experiment_id],
                             filter_string=f"tags.mlflow.parentRunId = '{parent}' and tags.model_type = 'baseline'")
    base = {c.replace("metrics.", ""): float(sib.iloc[0][c]) for c in sib.columns
            if c.startswith("metrics.test_")} if len(sib) else {}

    out = resolve(p["champion_dir"])
    old = json.loads((out / "metadata.json").read_text(encoding="utf-8")) if (out / "metadata.json").exists() else {}
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(mlflow.artifacts.download_artifacts(f"models:/{p['registered_model_name']}@champion"), out / "model")
    save_json({
        "best_model": mv.tags.get("model_type", run.data.tags.get("model_type")),
        "run_id": mv.run_id,
        "gate_passed": True,
        "test_period": old.get("test_period", ["?", "?"]),
        "best": {k: v for k, v in m.items() if k.startswith(("test_", "cv_roc_auc_mean"))},
        "baseline": base,
        "registered_model": p["registered_model_name"],
        "version": int(mv.version),
        "features": old.get("features"),
        "feature_params": params["features"],
    }, out / "metadata.json")
    log.info("📦 Exported %s v%s (@champion) → %s", p["registered_model_name"], mv.version, out)


if __name__ == "__main__":
    main()
