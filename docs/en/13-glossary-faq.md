# 13 · Glossary & FAQ

> 🌐 **English** · [Español](../es/13-glossary-faq.md) · ⬅️ [12 · Notebook → production](12-notebook-to-production.md) · [🏠 README](../../README.md)

## 📖 Glossary (in plain words)

| Term | Plain words |
|---|---|
| **MLOps** | Practices to take ML models from a notebook to reliable, repeatable production |
| **Candle (OHLCV)** | Summary of 1 hour of trading: Open, High, Low, Close, Volume |
| **H1** | Timeframe of 1 hour per candle |
| **Binary classification** | Predicting one of two answers: UP (1) or DOWN (0) |
| **Feature** | A numeric "clue" given to the model |
| **Target / label** | The right answer the model must learn |
| **Baseline** | The dumbest reasonable model (always UP). Anything real must beat it |
| **Data leakage** | A clue that secretly contains future information → fake great results |
| **Overfitting** | Memorizing the past (noise) instead of learning patterns |
| **Walk-forward CV** | Validation that always trains on the past and tests on what comes next |
| **ROC-AUC** | How well the model ranks UPs above DOWNs. 0.5 = coin, 1.0 = perfect |
| **Pipeline (DVC)** | Chain of stages with declared inputs/outputs; re-runs only what changed |
| **DVC remote / storage** | Where data versions live (here a local folder; in companies S3/GCS…) |
| **Experiment tracking** | Recording params, metrics and artifacts of every training run (MLflow) |
| **Run** | One training attempt recorded in MLflow |
| **Artifact** | A file saved with a run (plot, model, report) |
| **Model signature** | The model's "contract": which inputs it accepts and what it returns |
| **Model Registry** | Catalog of approved model versions |
| **Alias (@champion)** | A movable label pointing to the version in production |
| **Quality gate** | Written rules a model must pass before being promoted |
| **API** | A door through which programs talk to each other over HTTP |
| **Endpoint** | One specific door of the API (e.g. `/predict`) |
| **Docker image / container** | The packed box / the box running |
| **Registry (ghcr.io)** | Where Docker images are stored and shared |
| **CI** | Automatic checks on every change |
| **CD** | Automatic delivery of changes that passed CI |
| **Data drift** | Today's data no longer looks like the training data |
| **KS test** | Statistical test that measures how different two distributions are (0–1) |
| **Training/serving skew** | Computing features differently in training vs production (a silent bug) |

## ❓ FAQ

**Can I get rich with this model?**
No. It's ~51.5% right and lost to buy & hold in the test year. It's a teaching tool. Not financial advice.

**`MT5 initialize() failed`**
Open the MetaTrader 5 terminal and log in (a demo account works). The Python package talks to the running terminal.

**My broker has no `XAUUSD`**
Add its name to `params.yaml → data.symbol_candidates` (the extract script tells you which names it found).

**I'm on Mac/Linux**
Everything works except extraction. Use the sample CSV (see [01 · Setup](01-setup.md#-no-metatrader-5-maclinux-or-no-account)).

**`dvc repro` says "didn't change, skipping"**
That's the point! Force a stage with `dvc repro -f <stage>` (e.g. `-f extract` to download fresh data).

**`dvc pull` fails on another PC**
The storage is a local folder on *your* PC. For teams, use a shared/cloud remote: `dvc remote modify localstorage url s3://bucket/path`.

**Port 8000 is already in use**
`$env:API_PORT=8010; docker compose up` (or `uvicorn src.api.main:app --port 8010`).

**Why does CI train on only 4,000 candles?**
The GitHub robot has no MT5 and can't reach your local DVC storage. CI checks that the *code* works; the *real* model is trained on your PC and checked by the quality gate.

**Where do I see the CI results?**
https://github.com/MirandaCR/GoldMLFlow/actions → click a run → **Summary**.

**How do I roll back to an older model?**
In the MLflow UI (Models → gold-direction-h1) move the `@champion` alias to the older version, then re-export with `python scripts/export_champion.py`, then commit `models/champion`.

---
[🏠 Back to the README](../../README.md)
