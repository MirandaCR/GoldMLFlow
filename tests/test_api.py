"""API tests: spin up the app in-memory with the committed champion model.
Pruebas de la API: levanta la app en memoria con el modelo campeón del repo."""
import pytest
from fastapi.testclient import TestClient

from src.api.main import MODEL_DIR, app

pytestmark = pytest.mark.skipif(not (MODEL_DIR / "metadata.json").exists(),
                                reason="no champion model exported yet")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "model_loaded": True}


def test_model_info(client):
    body = client.get("/model-info").json()
    assert body["model"] != "baseline"
    assert "test_roc_auc" in body["metrics"]


def test_predict_from_candles(client, sample_raw):
    candles = sample_raw.tail(300)[["time", "open", "high", "low", "close", "volume"]]
    r = client.post("/predict", json={"candles": candles.to_dict(orient="records")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["direction"] in {"UP", "DOWN"}
    assert 0 <= body["prob_up"] <= 1
    assert body["based_on_candle"].startswith(str(candles.time.iloc[-1])[:13].replace(" ", "T"))


def test_predict_rejects_too_few_candles(client, sample_raw):
    candles = sample_raw.tail(10)[["time", "open", "high", "low", "close", "volume"]]
    r = client.post("/predict", json={"candles": candles.to_dict(orient="records")})
    assert r.status_code == 422


def test_predict_history_returns_one_point_per_candle(client, sample_raw):
    candles = sample_raw.tail(400)[["time", "open", "high", "low", "close", "volume"]]
    r = client.post("/predict/history", json={"candles": candles.to_dict(orient="records")})
    assert r.status_code == 200, r.text
    points = r.json()["points"]
    assert 150 <= len(points) <= 400
    assert all(0 <= p["prob_up"] <= 1 for p in points)
