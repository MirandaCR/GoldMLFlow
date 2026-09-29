"""Data quality tests / Pruebas de calidad de datos."""
from src.data.validate import run_checks


def test_sample_data_passes_validation(sample_raw, params):
    checks = run_checks(sample_raw, min_rows=1000, max_missing_pct=0.0)
    assert all(checks.values()), checks


def test_validation_catches_broken_candle(sample_raw):
    broken = sample_raw.copy()
    broken.loc[10, "high"] = broken.loc[10, "low"] - 1  # impossible candle
    checks = run_checks(broken, min_rows=1000, max_missing_pct=0.0)
    assert not checks["high_is_highest"]


def test_validation_catches_duplicates(sample_raw):
    dup = sample_raw.copy()
    dup.loc[5, "time"] = dup.loc[4, "time"]
    assert not run_checks(dup, 1000, 0.0)["no_duplicated_timestamps"]
