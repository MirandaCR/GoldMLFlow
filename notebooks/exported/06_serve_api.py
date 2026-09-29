# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 🍽️ 06 · Serve the model: API + Docker
# ### Servir el modelo: API + Docker
#
# | | |
# |---|---|
# | 🍳 **Analogy / Analogía** | *The waiter (API) takes orders; the food-truck (Docker) can park anywhere* · *El mesero (API) toma pedidos; el food-truck (Docker) se estaciona en cualquier lugar* |
# | 🎯 **Goal / Objetivo** | Let any program ask "UP or DOWN?" over HTTP · Que cualquier programa pregunte "¿SUBE o BAJA?" por HTTP |
# | 🏭 **Becomes / Se convierte en** | `src/api/main.py`, `Dockerfile`, `docker-compose.yml` |
#
# ```
#   📱 client / trading bot                🐳 Docker container
#   ─────────────────────                  ┌────────────────────────────────────┐
#   POST /predict  {last 300 candles} ───▶ │ FastAPI                            │
#                                          │  1. make_features(with_target=False)│
#   {"direction":"UP","prob_up":0.53} ◀─── │  2. champion.predict_proba()       │
#                                          └────────────────────────────────────┘
# ```

# %%
import os
import sys
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import json

import pandas as pd
from fastapi.testclient import TestClient

from src.api.main import app

# %% [markdown]
# **EN:** `TestClient` starts the API *inside this notebook* (no server needed) — the same thing the tests in CI do.
# **ES:** `TestClient` levanta la API *dentro del notebook* (sin servidor) — lo mismo que hacen los tests en el CI.

# %%
client = TestClient(app)
client.__enter__()  # runs the startup: loads the champion model once

print("GET /health →", client.get("/health").json())

# %%
print(json.dumps(client.get("/model-info").json(), indent=2)[:800])

# %% [markdown]
# ## 🔮 Ask for a prediction / Pedir una predicción

# %%
candles = pd.read_csv("data/sample/xauusd_h1_sample.csv").tail(300)
payload = {"candles": candles[["time", "open", "high", "low", "close", "volume"]].to_dict(orient="records")}
r = client.post("/predict", json=payload)
print(r.status_code, r.json())

# %% [markdown]
# ## 🛡️ The API protects itself / La API se protege sola
# **EN:** Pydantic validates the input. Too few candles or a negative price → clear error (422), not a crash.
# **ES:** Pydantic valida la entrada. Pocas velas o un precio negativo → error claro (422), no una caída.

# %%
bad = {"candles": payload["candles"][:10]}
r = client.post("/predict", json=bad)
print(r.status_code, r.json()["detail"][0]["msg"])

# %%
client.__exit__(None, None, None)

# %% [markdown]
# ## 🐳 Now in a container / Ahora en un contenedor
#
# ```powershell
# docker compose up --build          # builds the image and starts the API
# # open http://localhost:8000/docs  → interactive Swagger page ("Try it out")
# python scripts/live_demo.py        # real MT5 candles → API → prediction for the next hour
# ```
#
# **EN — Why Docker?** "It works on my machine" disappears: the image contains Python, the libraries (exact
# versions), the code and the model. The same image runs on your laptop, in CI and on a cloud server.
#
# **ES — ¿Por qué Docker?** Se acaba el "en mi máquina funciona": la imagen contiene Python, las librerías (versiones
# exactas), el código y el modelo. La misma imagen corre en tu laptop, en el CI y en un servidor en la nube.
#
# ---
# ## 🔁 From notebook to production / Del notebook a producción
#
# | Notebook | Production |
# |---|---|
# | `TestClient` in a cell | `tests/test_api.py` — runs on every push |
# | Model loaded by hand | Loaded **once** at startup (`lifespan`) from `MODEL_DIR` |
# | Python on your PC | `Dockerfile` (slim image, non-root user, healthcheck) |
# | — | **CD** pipeline builds & publishes the image to `ghcr.io` automatically |
