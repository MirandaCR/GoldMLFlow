"""CI QUALITY GATE — is the champion committed to the repo good enough?

EN: GitHub Actions runs this on every push/PR. If someone commits a champion
    model whose metrics don't pass the thresholds in params.yaml, CI fails
    and the change can't be merged.
ES: GitHub Actions ejecuta esto en cada push/PR. Si alguien sube un modelo
    campeón cuyas métricas no pasan los umbrales de params.yaml, el CI falla
    y el cambio no se puede fusionar.

Run / Ejecutar:  python -m src.models.check_gate
"""
from __future__ import annotations

import json
import sys

from src.models.gate import gate
from src.utils import get_logger, load_params, resolve

log = get_logger("check_gate")


def main() -> int:
    p = load_params()["evaluate"]
    meta_path = resolve(p["champion_dir"]) / "metadata.json"
    if not meta_path.exists():
        log.error("No champion found at %s", meta_path)
        return 1
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    checks = gate(meta["best"], meta["baseline"], p)

    lines = [f"### 🏆 Champion: `{meta['best_model']}` v{meta.get('version', '?')}", "",
             "| Check | Result |", "|---|---|"]
    lines += [f"| {k} | {'✅' if ok else '❌'} |" for k, ok in checks.items()]
    lines += ["", "| Metric | Champion | Baseline |", "|---|---|---|"]
    for m in ("test_roc_auc", "test_accuracy", "test_f1", "test_strategy_return"):
        lines.append(f"| {m} | {meta['best'].get(m, 0):.4f} | {meta['baseline'].get(m, 0):.4f} |")
    print("\n".join(lines))

    if not all(checks.values()):
        log.error("Quality gate FAILED")
        return 1
    log.info("Quality gate passed ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
