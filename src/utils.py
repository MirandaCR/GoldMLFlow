"""Small helpers shared by every stage.

EN: Every script reads its settings from params.yaml, so nothing is hard-coded.
ES: Cada script lee su configuración de params.yaml; nada queda "quemado" en el código.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_params(path: str | Path = ROOT / "params.yaml") -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_logger(name: str) -> logging.Logger:
    # Windows consoles default to cp1252 → force UTF-8 so ✅ ❌ → print fine
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(name)


def save_json(obj: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def resolve(path: str | Path) -> Path:
    """Paths in params.yaml are relative to the project root."""
    p = Path(path)
    return p if p.is_absolute() else ROOT / p
