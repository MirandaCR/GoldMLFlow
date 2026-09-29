"""The quality-gate rule, shared by promote.py (local) and check_gate.py (CI).
La regla del control de calidad, compartida por promote.py (local) y check_gate.py (CI)."""


def gate(best: dict, baseline: dict, p: dict) -> dict[str, bool]:
    metric = p["primary_metric"]
    checks = {f"{metric} >= {p['min_roc_auc']}": best[f"test_{metric}"] >= p["min_roc_auc"]}
    if p["must_beat_baseline"]:
        checks["beats baseline (roc_auc)"] = best["test_roc_auc"] > baseline["test_roc_auc"]
        checks["beats baseline (accuracy)"] = best["test_accuracy"] > baseline["test_accuracy"]
    return checks
