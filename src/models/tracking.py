"""Where does MLflow save things? / ¿Dónde guarda MLflow las cosas?

EN: Default = a local SQLite file (mlflow.db) + artifacts in ./mlartifacts.
    Set MLFLOW_TRACKING_URI=http://localhost:5000 to use the shared server
    started with `docker compose up mlflow` (the "team" setup).
ES: Por defecto = un archivo SQLite local (mlflow.db) + artefactos en ./mlartifacts.
    Define MLFLOW_TRACKING_URI=http://localhost:5000 para usar el servidor
    compartido que levanta `docker compose up mlflow` (el modo "equipo").
"""
from __future__ import annotations

import os

import mlflow

from src.utils import ROOT

DEFAULT_URI = f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}"


def setup_mlflow(experiment_name: str) -> str:
    uri = os.environ.get("MLFLOW_TRACKING_URI", DEFAULT_URI)
    mlflow.set_tracking_uri(uri)
    if mlflow.get_experiment_by_name(experiment_name) is None:
        location = None if uri.startswith("http") else (ROOT / "mlartifacts").as_uri()
        mlflow.create_experiment(experiment_name, artifact_location=location)
    mlflow.set_experiment(experiment_name)
    return uri
