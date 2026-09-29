import pandas as pd
import pytest

from src.utils import load_params, resolve


@pytest.fixture(scope="session")
def params():
    return load_params()


@pytest.fixture(scope="session")
def sample_raw(params):
    """The small CSV committed to Git (last ~4000 H1 candles)."""
    return pd.read_csv(resolve(params["data"]["sample_path"]))
