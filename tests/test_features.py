"""Feature tests — the most important one checks there is NO data leakage.
Pruebas de features — la más importante verifica que NO haya fuga de datos."""
import numpy as np

from src.features.build import feature_columns, make_features


def test_target_is_next_candle_direction(sample_raw, params):
    f = make_features(sample_raw, params["features"])
    nxt = f["close"].shift(-1)
    # Wherever the next row is the next candle, target must equal (next close > close)
    ok = f["target"].iloc[:-1] == (nxt.iloc[:-1] > f["close"].iloc[:-1]).astype(int)
    assert ok.mean() == 1.0


def test_no_leakage_features_ignore_the_future(sample_raw, params):
    """Changing FUTURE prices must not change today's clues.
    Cambiar precios FUTUROS no debe cambiar las pistas de hoy."""
    base = make_features(sample_raw, params["features"], with_target=False)
    tampered = sample_raw.copy()
    tampered.loc[tampered.index[-100:], ["open", "high", "low", "close"]] *= 1.5
    after = make_features(tampered, params["features"], with_target=False)

    cols = feature_columns(base)
    n = len(base) - 100
    assert np.allclose(base[cols].iloc[:n].values, after[cols].iloc[:n].values, equal_nan=True)


def test_no_missing_values_and_binary_target(sample_raw, params):
    f = make_features(sample_raw, params["features"])
    assert not f.isna().any().any()
    assert set(f["target"].unique()) <= {0, 1}


def test_inference_mode_keeps_last_candle(sample_raw, params):
    train_mode = make_features(sample_raw, params["features"], with_target=True)
    serve_mode = make_features(sample_raw, params["features"], with_target=False)
    assert len(serve_mode) == len(train_mode) + 1
    assert "target" not in serve_mode.columns
