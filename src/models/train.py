"""STAGE 4 — TRAIN: try several models and write EVERYTHING down in MLflow.

EN: Think of MLflow as a lab notebook that never forgets. For every model we
    record: settings (params), scores (metrics), charts (artifacts) and the
    model file itself — so any result can be compared and reproduced later.
ES: Piensa en MLflow como un cuaderno de laboratorio que nunca olvida. Para cada
    modelo anotamos: configuración (params), notas (métricas), gráficos
    (artefactos) y el propio archivo del modelo — para comparar y reproducir.

Time-series rule: NEVER shuffle. We train on the past and test on the future.
Regla de series de tiempo: NUNCA mezclar. Entrenamos con el pasado, probamos con el futuro.

    |■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■ train (80%) ■■■■■■■■■■■■■■■■|□□□ test (20%) □□□|
     past / pasado  ───────────────────────────────────────────────────────▶  future / futuro

Run / Ejecutar:  python -m src.models.train [--input data/processed/features.csv]
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mlflow  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from mlflow.models import infer_signature  # noqa: E402
from sklearn.dummy import DummyClassifier  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    ConfusionMatrixDisplay,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from xgboost import XGBClassifier  # noqa: E402

from src.features.build import feature_columns  # noqa: E402
from src.models.tracking import setup_mlflow  # noqa: E402
from src.utils import get_logger, load_params, resolve, save_json  # noqa: E402

log = get_logger("train")


def build_models(p: dict, seed: int) -> dict[str, Pipeline]:
    """Every model is a Pipeline, so scaling travels WITH the model to the API."""
    m = p["models"]
    return {
        # The "coin flip" to beat: always predicts the most common answer
        # La "moneda al aire" a vencer: siempre predice la respuesta más común
        "baseline": Pipeline([("model", DummyClassifier(strategy="most_frequent"))]),
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(**m["logistic_regression"], random_state=seed)),
        ]),
        "random_forest": Pipeline([
            ("model", RandomForestClassifier(**m["random_forest"], random_state=seed, n_jobs=-1)),
        ]),
        "xgboost": Pipeline([
            ("model", XGBClassifier(**m["xgboost"], random_state=seed, eval_metric="logloss", n_jobs=-1)),
        ]),
    }


def classification_metrics(y_true, proba) -> dict[str, float]:
    pred = (proba >= 0.5).astype(int)
    return {
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, proba) if len(np.unique(y_true)) > 1 else 0.5,
    }


def backtest(close: pd.Series, proba: np.ndarray) -> pd.DataFrame:
    """Toy strategy: buy if model says UP, sell if DOWN. No costs — for learning only!
    Estrategia de juguete: compra si dice SUBE, vende si dice BAJA. Sin costos — ¡solo para aprender!"""
    next_ret = close.shift(-1) / close - 1
    position = np.where(proba >= 0.5, 1, -1)
    bt = pd.DataFrame({"market": next_ret.fillna(0).values})
    bt["strategy"] = position * bt["market"]
    bt["equity_market"] = (1 + bt["market"]).cumprod()
    bt["equity_strategy"] = (1 + bt["strategy"]).cumprod()
    return bt


def plot_confusion(y_true, proba, title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ConfusionMatrixDisplay.from_predictions(
        y_true, (proba >= 0.5).astype(int), display_labels=["DOWN ↓", "UP ↑"],
        cmap="Blues", ax=ax, colorbar=False)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def plot_equity(bt: pd.DataFrame, times: pd.Series, title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(times.values, bt["equity_market"], label="Buy & Hold gold", color="#b8860b")
    ax.plot(times.values, bt["equity_strategy"], label="Model strategy", color="#1f77b4")
    ax.axhline(1, color="grey", lw=0.8, ls="--")
    ax.set_title(title)
    ax.set_ylabel("Growth of $1")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def plot_importance(pipe: Pipeline, features: list[str], path: Path) -> bool:
    model = pipe.named_steps["model"]
    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    elif hasattr(model, "coef_"):
        values = np.abs(model.coef_[0])
    else:
        return False
    s = pd.Series(values, index=features).sort_values()
    fig, ax = plt.subplots(figsize=(6, 5))
    s.plot.barh(ax=ax, color="#2a9d8f")
    ax.set_title("Which clues matter most? / ¿Qué pistas importan más?")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return True


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "no-git"


def main() -> None:
    params = load_params()
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=params["features"]["processed_path"])
    parser.add_argument("--output", default="reports/train_results.json")
    args = parser.parse_args()

    p = params["train"]
    df = pd.read_csv(resolve(args.input), parse_dates=["time"])
    features = feature_columns(df)

    # ── Chronological split (NO shuffle!) / División cronológica (¡SIN mezclar!) ──
    cut = int(len(df) * (1 - p["test_size"]))
    train, test = df.iloc[:cut], df.iloc[cut:].reset_index(drop=True)
    X_train, y_train = train[features], train["target"]
    X_test, y_test = test[features], test["target"]
    log.info("Train: %s → %s (%d) | Test: %s → %s (%d)",
             train.time.min(), train.time.max(), len(train),
             test.time.min(), test.time.max(), len(test))

    uri = setup_mlflow(p["experiment_name"])
    log.info("MLflow tracking URI: %s", uri)

    results = []
    tscv = TimeSeriesSplit(n_splits=p["cv_splits"])
    with mlflow.start_run(run_name="training-session") as parent:
        mlflow.set_tags({"git_commit": git_commit(), "data_file": args.input})
        mlflow.log_params({"n_features": len(features), "train_rows": len(train),
                           "test_rows": len(test), "train_end": str(train.time.max())})

        for name, pipe in build_models(p, p["random_state"]).items():
            with mlflow.start_run(run_name=name, nested=True) as run:
                log.info("── Training %s", name)
                mlflow.set_tag("model_type", name)
                mlflow.log_params({k: v for k, v in pipe.named_steps["model"].get_params().items()
                                   if isinstance(v, (int, float, str, bool)) or v is None})

                # 1) Walk-forward cross-validation: "practice exams" on the past
                cv_auc, cv_acc = [], []
                for fold, (tr, va) in enumerate(tscv.split(X_train)):
                    pipe.fit(X_train.iloc[tr], y_train.iloc[tr])
                    pr = pipe.predict_proba(X_train.iloc[va])[:, 1]
                    m = classification_metrics(y_train.iloc[va], pr)
                    cv_auc.append(m["roc_auc"])
                    cv_acc.append(m["accuracy"])
                    mlflow.log_metric("cv_roc_auc", m["roc_auc"], step=fold)
                mlflow.log_metrics({"cv_roc_auc_mean": float(np.mean(cv_auc)),
                                    "cv_roc_auc_std": float(np.std(cv_auc)),
                                    "cv_accuracy_mean": float(np.mean(cv_acc))})

                # 2) Final exam: fit on all the past, test on the unseen future
                pipe.fit(X_train, y_train)
                proba = pipe.predict_proba(X_test)[:, 1]
                metrics = {f"test_{k}": float(v) for k, v in classification_metrics(y_test, proba).items()}

                bt = backtest(test["close"], proba)
                metrics["test_strategy_return"] = float(bt["equity_strategy"].iloc[-1] - 1)
                metrics["test_buyhold_return"] = float(bt["equity_market"].iloc[-1] - 1)
                mlflow.log_metrics(metrics)

                # 3) Charts → artifacts
                with tempfile.TemporaryDirectory() as tmp:
                    tmp = Path(tmp)
                    plot_confusion(y_test, proba, f"{name} — test", tmp / "confusion_matrix.png")
                    plot_equity(bt, test["time"], f"{name} — toy backtest (no costs)", tmp / "equity_curve.png")
                    plot_importance(pipe, features, tmp / "feature_importance.png")
                    mlflow.log_artifacts(str(tmp), artifact_path="plots")

                # 4) The model itself + its "contract" (signature: inputs → output)
                signature = infer_signature(X_test.head(50), proba[:50])
                mlflow.sklearn.log_model(pipe, name="model", signature=signature,
                                         input_example=X_test.head(3))

                log.info("   test AUC=%.4f acc=%.4f strategy=%+.2f%%", metrics["test_roc_auc"],
                         metrics["test_accuracy"], metrics["test_strategy_return"] * 100)
                results.append({"model": name, "run_id": run.info.run_id,
                                "cv_roc_auc_mean": float(np.mean(cv_auc)), **metrics})

    save_json({"parent_run_id": parent.info.run_id, "tracking_uri": uri,
               "features": features, "test_start": str(test.time.min()),
               "test_end": str(test.time.max()), "results": results}, resolve(args.output))
    log.info("Saved %s — open the UI with:  mlflow ui --backend-store-uri %s", args.output, uri)


if __name__ == "__main__":
    main()
