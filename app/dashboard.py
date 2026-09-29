"""STAGE 8 — DASHBOARD: a visual app to SEE and USE the model (Streamlit).

EN: The "restaurant dining room". A non-technical person opens a web page and:
      🔮 sees gold candles + the model's call for the next hour (UP/DOWN gauge)
      🎯 sees where the model was right/wrong on recent candles
      🏆 compares the models trained in the pipeline (leaderboard, quality gate)
      📡 checks if the market drifted (time to retrain?)
      🗺️ follows the whole MLOps flow, stage by stage
    It talks to the model through the API (like any real client would).
ES: El "comedor del restaurante". Una persona no técnica abre una página web y:
      🔮 ve las velas del oro + la predicción para la próxima hora (indicador SUBE/BAJA)
      🎯 ve dónde acertó/falló el modelo en las velas recientes
      🏆 compara los modelos del pipeline (tabla de posiciones, control de calidad)
      📡 revisa si el mercado cambió (¿toca reentrenar?)
      🗺️ recorre todo el flujo MLOps, etapa por etapa
    Habla con el modelo a través de la API (como lo haría cualquier cliente real).

Run / Ejecutar:
    streamlit run app/dashboard.py                  (uses the API if it's up, else loads the model in-process)
    docker compose up --build                       → http://localhost:8501
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
API_URL = os.environ.get("API_URL", "http://localhost:8000")
GOLD, UP_C, DOWN_C, GREY = "#D4A017", "#2A9D8F", "#E63946", "#8D99AE"

st.set_page_config(page_title="GoldMLFlow · MLOps for Dummies", page_icon="🥇", layout="wide")

# ─────────────────────────── Texts (ES / EN) ───────────────────────────
T = {
    "es": {
        "title": "🥇 GoldMLFlow — ¿El oro sube o baja la próxima hora?",
        "subtitle": "Ejemplo educativo de MLOps · MetaTrader 5 → DVC → MLflow → API → Docker → CI/CD",
        "source": "Fuente de datos", "src_mt5": "MetaTrader 5 (en vivo)", "src_sample": "Muestra en Git (CSV)",
        "src_upload": "Subir CSV", "n_candles": "Velas a mostrar", "backend": "Motor de predicción",
        "tab_pred": "🔮 Predicción", "tab_models": "🏆 Modelos", "tab_drift": "📡 Drift", "tab_flow": "🗺️ Flujo MLOps",
        "last_price": "Último precio", "chg24": "Cambio 24h", "model": "Modelo campeón", "hit": "Acierto en la ventana",
        "next": "Próxima vela (H1)", "up": "SUBE ▲", "down": "BAJA ▼", "prob": "Probabilidad de SUBIR",
        "based": "Basado en la vela cerrada de", "legend_ok": "acierto", "legend_bad": "fallo",
        "chart_title": "Velas H1 del oro + predicciones del modelo", "prob_axis": "P(SUBE)",
        "disclaimer": "⚠️ Ejemplo educativo. No es asesoría financiera.",
        "how_read": "¿Cómo leer esto?",
        "how_read_md": "- **Velas**: verde = la hora cerró arriba, roja = abajo.\n"
                       "- **Triángulos**: lo que dijo el modelo *antes* de cada hora (▲ SUBE bajo la vela, ▼ BAJA encima). Con color = acertó ✔, vacío gris = falló ✘.\n"
                       "- **Panel inferior**: probabilidad de subir. Por encima de la línea de 50% → dice SUBE.\n"
                       "- Un acierto cercano al **50%** es normal: el mercado horario es casi aleatorio.",
        "leader": "Tabla de posiciones (datos de test, nunca vistos)", "gate": "🚦 Control de calidad",
        "passed": "APROBADO → modelo promovido a @champion", "failed": "RECHAZADO → se mantiene el campeón anterior",
        "vs_coin": "ROC-AUC vs moneda al aire (0.5)", "money": "Backtest de juguete (sin comisiones)",
        "strategy": "Estrategia del modelo", "buyhold": "Comprar y mantener",
        "money_note": "Superar el 50% no garantiza ganar dinero: aquí mantener oro ganó más que el modelo.",
        "drift_title": "¿Qué tan distinto es el mercado de hoy vs el de entrenamiento? (KS: 0 = igual, 1 = totalmente distinto)",
        "retrain": "Recomendación: REENTRENAR (dvc repro -f extract)", "no_retrain": "El mercado sigue parecido: no hace falta reentrenar",
        "no_report": "Aún no hay reporte. Ejecuta `dvc repro`.",
        "api_ok": "API conectada", "api_local": "API no disponible → modelo cargado localmente",
        "flow_intro": "Cada caja es una etapa. Así viaja el dato desde MetaTrader 5 hasta esta pantalla:",
    },
    "en": {
        "title": "🥇 GoldMLFlow — Will gold go UP or DOWN next hour?",
        "subtitle": "Educational MLOps example · MetaTrader 5 → DVC → MLflow → API → Docker → CI/CD",
        "source": "Data source", "src_mt5": "MetaTrader 5 (live)", "src_sample": "Sample in Git (CSV)",
        "src_upload": "Upload CSV", "n_candles": "Candles to show", "backend": "Prediction engine",
        "tab_pred": "🔮 Prediction", "tab_models": "🏆 Models", "tab_drift": "📡 Drift", "tab_flow": "🗺️ MLOps flow",
        "last_price": "Last price", "chg24": "24h change", "model": "Champion model", "hit": "Hit rate in window",
        "next": "Next candle (H1)", "up": "UP ▲", "down": "DOWN ▼", "prob": "Probability of UP",
        "based": "Based on the closed candle of", "legend_ok": "right", "legend_bad": "wrong",
        "chart_title": "Gold H1 candles + model predictions", "prob_axis": "P(UP)",
        "disclaimer": "⚠️ Educational example. Not financial advice.",
        "how_read": "How to read this?",
        "how_read_md": "- **Candles**: green = the hour closed higher, red = lower.\n"
                       "- **Triangles**: what the model said *before* each hour (▲ UP below the candle, ▼ DOWN above it). Coloured = right ✔, hollow grey = wrong ✘.\n"
                       "- **Bottom panel**: probability of UP. Above the 50% line → it says UP.\n"
                       "- A hit rate near **50%** is normal: hourly markets are almost random.",
        "leader": "Leaderboard (test data, never seen)", "gate": "🚦 Quality gate",
        "passed": "PASSED → model promoted to @champion", "failed": "FAILED → previous champion stays",
        "vs_coin": "ROC-AUC vs coin flip (0.5)", "money": "Toy backtest (no fees)",
        "strategy": "Model strategy", "buyhold": "Buy & hold",
        "money_note": "Beating 50% doesn't guarantee profit: here simply holding gold earned more than the model.",
        "drift_title": "How different is today's market vs the training one? (KS: 0 = same, 1 = totally different)",
        "retrain": "Recommendation: RETRAIN (dvc repro -f extract)", "no_retrain": "Market still similar: no need to retrain",
        "no_report": "No report yet. Run `dvc repro`.",
        "api_ok": "API connected", "api_local": "API not available → model loaded in-process",
        "flow_intro": "Each box is a stage. This is how data travels from MetaTrader 5 to this screen:",
    },
}

lang = st.sidebar.radio("🌐 Idioma / Language", ["es", "en"], format_func=lambda x: {"es": "Español", "en": "English"}[x],
                        horizontal=True)
t = T[lang]

st.markdown(f"""
<style>
.big-card {{border-radius:18px;padding:22px;text-align:center;color:white;}}
.big-card h1 {{margin:0;font-size:3rem;color:white}}
.stage {{border-radius:14px;padding:12px;text-align:center;border:2px solid {GOLD};min-height:150px}}
.stage h3 {{margin:4px 0;font-size:1.05rem}}
.stage p {{font-size:.82rem;margin:0}}
.arrow {{text-align:center;font-size:2rem;color:{GOLD};padding-top:45px}}
</style>""", unsafe_allow_html=True)

st.title(t["title"])
st.caption(t["subtitle"])


# ─────────────────────────── Backend: API or in-process ───────────────────────────
@st.cache_resource
def local_client():
    """Fallback: run the SAME FastAPI app in-process (no duplicated logic)."""
    from fastapi.testclient import TestClient

    from src.api.main import app
    client = TestClient(app)
    client.__enter__()
    return client


def api_available() -> bool:
    try:
        # /model-info (not just /health) → make sure it's OUR API and not another app on that port
        return httpx.get(f"{API_URL}/model-info", timeout=2).status_code == 200
    except Exception:
        return False


USE_API = api_available()


def call(method: str, path: str, payload: dict | None = None) -> dict:
    if USE_API:
        r = httpx.request(method, f"{API_URL}{path}", json=payload, timeout=60)
    else:
        r = local_client().request(method, path, json=payload)
    r.raise_for_status()
    return r.json()


# ─────────────────────────── Data ───────────────────────────
def mt5_available() -> bool:
    try:
        import MetaTrader5  # noqa: F401
        return True
    except ImportError:
        return False


sources = ([t["src_mt5"]] if mt5_available() else []) + [t["src_sample"], t["src_upload"]]
source = st.sidebar.selectbox(t["source"], sources)
n_show = st.sidebar.slider(t["n_candles"], 48, 400, 120, step=24)


@st.cache_data(ttl=60, show_spinner=False)
def load_mt5(n: int) -> pd.DataFrame:
    from src.data.extract import fetch_rates
    from src.utils import load_params
    p = load_params()["data"]
    return fetch_rates(p["symbol_candidates"], p["timeframe"], n + 1).iloc[:-1]


@st.cache_data(show_spinner=False)
def load_csv(path_or_buffer) -> pd.DataFrame:
    return pd.read_csv(path_or_buffer, parse_dates=["time"])


need = n_show + 260  # extra history so the first shown candle already has its clues
if source == t["src_mt5"]:
    raw = load_mt5(need)
elif source == t["src_sample"]:
    raw = load_csv(ROOT / "data/sample/xauusd_h1_sample.csv").tail(need)
else:
    up = st.sidebar.file_uploader("CSV: time,open,high,low,close,volume", type="csv")
    if up is None:
        st.info("⬅️ " + t["src_upload"])
        st.stop()
    raw = load_csv(up).tail(need)

raw = raw.reset_index(drop=True)
st.sidebar.markdown("---")
st.sidebar.markdown(f"**{t['backend']}**")
if USE_API:
    st.sidebar.success(f"✅ {t['api_ok']}: {API_URL}")
else:
    st.sidebar.warning(f"🧩 {t['api_local']}")
st.sidebar.markdown("---")
st.sidebar.caption(t["disclaimer"])

info = call("GET", "/model-info")
payload = {"candles": [
    {"time": r.time.isoformat(), "open": r.open, "high": r.high, "low": r.low, "close": r.close,
     "volume": float(r.volume)} for r in raw.itertuples()]}

tab_pred, tab_models, tab_drift, tab_flow = st.tabs([t["tab_pred"], t["tab_models"], t["tab_drift"], t["tab_flow"]])

# ═══════════════════════════ TAB 1 · PREDICTION ═══════════════════════════
with tab_pred:
    pred = call("POST", "/predict", payload)
    hist = pd.DataFrame(call("POST", "/predict/history", payload)["points"])
    hist["time"] = pd.to_datetime(hist["time"])
    hist["next_close"] = hist["close"].shift(-1)
    hist["said_up"] = hist["prob_up"] >= 0.5
    hist["went_up"] = hist["next_close"] > hist["close"]
    hist["hit"] = hist["said_up"] == hist["went_up"]
    view = raw.tail(n_show)
    h = hist[hist.time.isin(view.time)].copy()
    judged = h.dropna(subset=["next_close"])
    hit_rate = judged["hit"].mean() if len(judged) else float("nan")

    c1, c2, c3, c4 = st.columns(4)
    last, prev24 = raw.close.iloc[-1], raw.close.iloc[-25] if len(raw) > 25 else raw.close.iloc[0]
    c1.metric(t["last_price"], f"${last:,.2f}")
    c2.metric(t["chg24"], f"{(last / prev24 - 1):+.2%}")
    c3.metric(t["model"], f"{info['model']} v{info['version']}", f"AUC {info['metrics']['test_roc_auc']:.3f}",
              delta_color="off")
    c4.metric(t["hit"], f"{hit_rate:.1%}", f"{len(judged)} h", delta_color="off")

    left, right = st.columns([3, 1.15])
    with right:
        is_up = pred["direction"] == "UP"
        color = UP_C if is_up else DOWN_C
        st.markdown(f"""<div class="big-card" style="background:{color}">
            <div style="font-size:1rem;opacity:.9">{t['next']}</div>
            <h1>{t['up'] if is_up else t['down']}</h1>
            <div style="font-size:.85rem;opacity:.9">{t['based']}<br><b>{pred['based_on_candle'][:16].replace('T', ' ')}</b></div>
            </div>""", unsafe_allow_html=True)
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=pred["prob_up"] * 100, number={"suffix": "%", "font": {"size": 40}},
            title={"text": t["prob"]},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": color},
                   "steps": [{"range": [0, 50], "color": "#fde2e4"}, {"range": [50, 100], "color": "#d8f3dc"}],
                   "threshold": {"line": {"color": "black", "width": 3}, "value": 50}}))
        gauge.update_layout(height=270, margin=dict(l=35, r=45, t=70, b=10))
        st.plotly_chart(gauge, use_container_width=True)

    with left:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.04)
        fig.add_trace(go.Candlestick(x=view.time, open=view.open, high=view.high, low=view.low, close=view.close,
                                     increasing_line_color=UP_C, decreasing_line_color=DOWN_C, name="XAUUSD H1"),
                      row=1, col=1)
        # Markers sit on the NEXT candle (the one being predicted)
        nv = view[["time", "high", "low"]].rename(columns={"time": "time_n", "high": "high_n", "low": "low_n"})
        nv["prev_time"] = view["time"].shift(1).values
        nxt = h.merge(nv, left_on="time", right_on="prev_time").dropna(subset=["next_close"])
        for said_up, sym, ycol, off in [(True, "triangle-up", "low_n", -0.0012), (False, "triangle-down", "high_n", 0.0012)]:
            for hit, lab in [(True, "✔ " + t["legend_ok"]), (False, "✘ " + t["legend_bad"])]:
                d = nxt[(nxt.said_up == said_up) & (nxt.hit == hit)]
                col = (UP_C if said_up else DOWN_C) if hit else "rgba(0,0,0,0)"
                edge = "#1b4332" if hit else GREY
                fig.add_trace(go.Scatter(
                    x=d.time_n, y=d[ycol] * (1 + off), mode="markers",
                    marker=dict(symbol=sym, size=11 if hit else 9, color=col, line=dict(width=1.5, color=edge)),
                    name=f"{t['up'] if said_up else t['down']} · {lab}",
                    hovertemplate="P(UP)=%{customdata:.1%}<extra></extra>", customdata=d.prob_up), row=1, col=1)
        fig.add_trace(go.Bar(x=h.time, y=h.prob_up, marker_color=[UP_C if p >= 0.5 else DOWN_C for p in h.prob_up],
                             name=t["prob_axis"], showlegend=False), row=2, col=1)
        fig.add_hline(y=0.5, line_dash="dash", line_color="black", row=2, col=1)
        lo, hi = h.prob_up.min(), h.prob_up.max()
        fig.update_yaxes(range=[min(0.4, lo - 0.01), max(0.6, hi + 0.01)], title=t["prob_axis"], row=2, col=1)
        fig.update_layout(height=560, title=t["chart_title"], xaxis_rangeslider_visible=False,
                          legend=dict(orientation="h", y=1.08, x=0), margin=dict(l=10, r=10, t=80, b=10))
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        st.plotly_chart(fig, use_container_width=True)

    with st.expander(f"❓ {t['how_read']}"):
        st.markdown(t["how_read_md"])


# ═══════════════════════════ TAB 2 · MODELS ═══════════════════════════
def read_json(rel: str) -> dict | None:
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


with tab_models:
    tr, mt = read_json("reports/train_results.json"), read_json("reports/metrics.json")
    if not tr or not mt:
        st.info(t["no_report"])
    else:
        res = pd.DataFrame(tr["results"]).sort_values("test_roc_auc", ascending=False)
        a, b = st.columns([1.3, 1])
        with a:
            st.subheader(t["leader"])
            colors = [GOLD if m == mt["best_model"] else ("#adb5bd" if m == "baseline" else "#8ab6d6") for m in res.model]
            fig = go.Figure(go.Bar(x=res.test_roc_auc, y=res.model, orientation="h", marker_color=colors,
                                   text=[f"{v:.4f}" for v in res.test_roc_auc], textposition="outside"))
            fig.add_vline(x=0.5, line_dash="dash", annotation_text="🪙 0.5")
            fig.update_layout(title=t["vs_coin"], height=320, xaxis_range=[0.48, max(0.53, res.test_roc_auc.max() + 0.006)],
                              yaxis_autorange="reversed", margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, use_container_width=True)
            show = res[["model", "test_roc_auc", "test_accuracy", "test_precision", "test_recall", "cv_roc_auc_mean"]]
            st.dataframe(show.set_index("model").style.format("{:.4f}").highlight_max(axis=0, color="#fff3bf"),
                         use_container_width=True)
        with b:
            st.subheader(t["gate"])
            (st.success if mt["gate_passed"] else st.error)(f"**{t['passed'] if mt['gate_passed'] else t['failed']}**")
            for k, ok in mt["gate_checks"].items():
                st.markdown(f"{'✅' if ok else '❌'} `{k}`")
            st.markdown(f"🏆 **{mt['best_model']}** · run `{mt['run_id'][:8]}` · test {mt['test_period'][0][:10]} → {mt['test_period'][1][:10]}")
            fig = go.Figure(go.Bar(x=[t["strategy"], t["buyhold"]],
                                   y=[mt["best"]["test_strategy_return"] * 100, mt["best"]["test_buyhold_return"] * 100],
                                   marker_color=["#1f77b4", GOLD],
                                   text=[f"{mt['best']['test_strategy_return']:+.1%}", f"{mt['best']['test_buyhold_return']:+.1%}"],
                                   textposition="outside"))
            fig.update_layout(title=t["money"], yaxis_title="%", height=300, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("💡 " + t["money_note"])


# ═══════════════════════════ TAB 3 · DRIFT ═══════════════════════════
with tab_drift:
    dr = read_json("reports/drift.json")
    if not dr:
        st.info(t["no_report"])
    else:
        (st.warning if dr["retrain_recommended"] else st.success)(
            f"**{t['retrain'] if dr['retrain_recommended'] else t['no_retrain']}** · drift = {dr['drift_share']:.0%}")
        d = pd.DataFrame(dr["features"]).sort_values("ks_stat")
        fig = go.Figure(go.Bar(x=d.ks_stat, y=d.feature, orientation="h",
                               marker_color=[DOWN_C if x else UP_C for x in d.drift]))
        fig.update_layout(title=t["drift_title"], height=520, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"train: {dr['reference_period'][0][:10]} → {dr['reference_period'][1][:10]}  ·  "
                   f"recent: {dr['current_period'][0][:10]} → {dr['current_period'][1][:10]}")


# ═══════════════════════════ TAB 4 · MLOPS FLOW ═══════════════════════════
STAGES = [  # icon, EN title, ES title, EN what, ES what, code, artifact that proves it ran
    ("⛏️", "1 · Extract", "1 · Extraer", "MetaTrader 5 → CSV (30,000 H1 candles)", "MetaTrader 5 → CSV (30.000 velas H1)",
     "src/data/extract.py", "data/raw/xauusd_h1.csv"),
    ("🗃️", "2 · Version data (DVC)", "2 · Versionar datos (DVC)", "Git for data: every dataset has a fingerprint",
     "Git para datos: cada dataset tiene una huella", "dvc.yaml · dvc.lock", "dvc.lock"),
    ("🔍", "3 · Validate", "3 · Validar", "Healthy data? If not, the pipeline stops", "¿Datos sanos? Si no, el pipeline se detiene",
     "src/data/validate.py", "reports/data_validation.json"),
    ("🧩", "4 · Features", "4 · Features", "Candles → 18 clues + target (UP/DOWN)", "Velas → 18 pistas + objetivo (SUBE/BAJA)",
     "src/features/build.py", "data/processed/features.csv"),
    ("🧪", "5 · Train + MLflow", "5 · Entrenar + MLflow", "4 models, everything logged", "4 modelos, todo registrado",
     "src/models/train.py", "reports/train_results.json"),
    ("🏆", "6 · Quality gate + Registry", "6 · Control de calidad + Registry", "Only a better model becomes @champion",
     "Solo un modelo mejor se vuelve @champion", "src/models/promote.py", "models/champion/metadata.json"),
    ("🍽️", "7 · API + Docker", "7 · API + Docker", "FastAPI serves the champion in a container",
     "FastAPI sirve al campeón en un contenedor", "src/api/main.py · Dockerfile", "Dockerfile"),
    ("⚙️", "8 · CI/CD", "8 · CI/CD", "GitHub Actions: test → gate → build → publish",
     "GitHub Actions: probar → gate → construir → publicar", ".github/workflows/", ".github/workflows/ci.yml"),
    ("📡", "9 · Monitor", "9 · Monitorear", "Data drift → retrain when the market changes",
     "Data drift → reentrenar cuando el mercado cambia", "src/monitoring/drift.py", "reports/drift.json"),
]
with tab_flow:
    st.markdown(t["flow_intro"])
    for row in (STAGES[0:3], STAGES[3:6], STAGES[6:9]):
        cols = st.columns([4, 1, 4, 1, 4])
        for i, (icon, en, es, what_en, what_es, code, artifact) in enumerate(row):
            exists = (ROOT / artifact).exists()
            with cols[i * 2]:
                st.markdown(f"""<div class="stage" style="background:{'#fff8e1' if exists else '#f1f3f5'}">
                    <div style="font-size:2rem">{icon}</div><h3>{es if lang == 'es' else en}</h3>
                    <p>{what_es if lang == 'es' else what_en}</p><p><code>{code}</code></p>
                    <p>{'✅' if exists else '⏳'}</p></div>""", unsafe_allow_html=True)
            if i < len(row) - 1:
                cols[i * 2 + 1].markdown('<div class="arrow">➜</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;font-size:1.6rem;color:#D4A017">⬇</div>', unsafe_allow_html=True)
    st.markdown("&nbsp;")
    st.markdown("```text\n"
                "  📡 drift ──(retrain)──▶ ⛏️ extract ──▶ … ──▶ 🏆 new champion only if it passes the gate 🔁\n"
                "```")
    lock = ROOT / "dvc.lock"
    if lock.exists():
        with st.expander("dvc.lock — " + ("la 'foto' exacta de cada etapa" if lang == "es" else "the exact 'snapshot' of every stage")):
            st.code(lock.read_text(encoding="utf-8")[:4000], language="yaml")
