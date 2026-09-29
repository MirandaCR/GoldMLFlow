"""STAGE 7 — MODEL API: the waiter that takes orders and brings back predictions.

EN: FastAPI app that loads the champion model and answers:
        GET  /health            → "am I alive?"
        GET  /model-info        → which model, which metrics
        POST /predict           → send the last candles, get UP/DOWN for the next one
        POST /predict/features  → send the clues directly
        POST /predict/history   → P(UP) for every candle sent (used by the dashboard)
    Interactive docs (Swagger): http://localhost:8000/docs
ES: App FastAPI que carga el modelo campeón y responde:
        GET  /health            → "¿estoy vivo?"
        GET  /model-info        → qué modelo, qué métricas
        POST /predict           → envía las últimas velas, recibe SUBE/BAJA para la siguiente
        POST /predict/features  → envía las pistas directamente
        POST /predict/history   → P(SUBE) para cada vela enviada (lo usa el dashboard)
    Documentación interactiva (Swagger): http://localhost:8000/docs

Run / Ejecutar:  uvicorn src.api.main:app --reload
Model source:    MODEL_DIR env var (default models/champion)
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException

from src.api.schemas import CandlesRequest, FeaturesRequest, History, ModelInfo, Prediction
from src.features.build import make_features
from src.utils import ROOT

MODEL_DIR = Path(os.environ.get("MODEL_DIR", ROOT / "models" / "champion"))
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load once at startup, not on every request / Se carga una vez al iniciar
    state["model"] = mlflow.sklearn.load_model(str(MODEL_DIR / "model"))
    state["meta"] = json.loads((MODEL_DIR / "metadata.json").read_text(encoding="utf-8"))
    yield
    state.clear()


app = FastAPI(
    title="🥇 Gold Direction API",
    description="Predicts if the next H1 gold candle closes UP or DOWN. "
                "Educational MLOps example — NOT financial advice.",
    version="1.0.0",
    lifespan=lifespan,
)


def _predict(X: pd.DataFrame) -> tuple[str, float]:
    prob_up = float(state["model"].predict_proba(X)[:, 1][-1])
    return ("UP" if prob_up >= 0.5 else "DOWN"), round(prob_up, 4)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": "model" in state}


@app.get("/model-info", response_model=ModelInfo)
def model_info() -> ModelInfo:
    m = state["meta"]
    return ModelInfo(model=m["best_model"], version=m.get("version"),
                     registered_model=m.get("registered_model"),
                     trained_test_period=m["test_period"],
                     metrics={k: round(v, 4) for k, v in m["best"].items()},
                     features=m["features"])


def _features_from_candles(req: CandlesRequest) -> pd.DataFrame:
    raw = pd.DataFrame([c.model_dump() for c in req.candles]).sort_values("time")
    feats = make_features(raw, state["meta"]["feature_params"], with_target=False)
    if feats.empty:
        raise HTTPException(422, "Not enough candles to compute features (send ≥ 250)")
    return feats


@app.post("/predict", response_model=Prediction)
def predict(req: CandlesRequest) -> Prediction:
    meta = state["meta"]
    feats = _features_from_candles(req)
    direction, prob = _predict(feats[meta["features"]])
    return Prediction(direction=direction, prob_up=prob, based_on_candle=feats["time"].iloc[-1],
                      model=meta["best_model"], model_version=meta.get("version"))


@app.post("/predict/features", response_model=Prediction)
def predict_features(req: FeaturesRequest) -> Prediction:
    meta = state["meta"]
    missing = set(meta["features"]) - set(req.features)
    if missing:
        raise HTTPException(422, f"Missing features: {sorted(missing)}")
    X = pd.DataFrame([req.features])[meta["features"]]
    direction, prob = _predict(X)
    return Prediction(direction=direction, prob_up=prob,
                      model=meta["best_model"], model_version=meta.get("version"))


@app.post("/predict/history", response_model=History)
def predict_history(req: CandlesRequest) -> History:
    meta = state["meta"]
    feats = _features_from_candles(req)
    probs = state["model"].predict_proba(feats[meta["features"]])[:, 1]
    points = [{"time": t, "close": c, "prob_up": round(float(p), 4)}
              for t, c, p in zip(feats["time"], feats["close"], probs, strict=True)]
    return History(model=meta["best_model"], points=points)
