import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import pandas as pd
from datetime import datetime

from pipeline import make_dataset, _add_weather, FEATURES
from predict import predict_arrival


@pytest.fixture(scope="module")
def ds():
    return make_dataset()


def test_predict_keys():
    r = predict_arrival("SOU", delay_minutes=10, now=datetime(2025, 3, 12, 9, 30))
    assert set(r) == {"predicted_delay_minutes", "predicted_arrival_time", "model_used"}


def test_arrival_time_format():
    r = predict_arrival("WEY", delay_minutes=0, now=datetime(2025, 6, 1, 8, 0))
    h, m = r["predicted_arrival_time"].split(":")
    assert 0 <= int(h) <= 23
    assert 0 <= int(m) <= 59


def test_delay_is_float():
    r = predict_arrival("SOU", 5, now=datetime(2025, 3, 12, 9, 0))
    assert isinstance(r["predicted_delay_minutes"], float)


def test_bad_station():
    with pytest.raises(ValueError, match="Unknown station"):
        predict_arrival("ZZZ", 5)


def test_first_delay_effect():
    t = datetime(2025, 3, 12, 9, 0)
    low  = predict_arrival("SOU", 10, now=t, first_delay=0.0)
    high = predict_arrival("SOU", 10, now=t, first_delay=20.0)
    assert high["predicted_delay_minutes"] >= low["predicted_delay_minutes"]


def test_weather_zeros(monkeypatch, tmp_path):
    import pipeline
    monkeypatch.setattr(pipeline, "INTERIM", tmp_path)
    stops = pd.DataFrame({"date_of_service": ["2024-01-01"], "hour": [9.0]})
    result = _add_weather(stops)
    assert result["temperature"].iloc[0] == 0.0
    assert result["precipitation"].iloc[0] == 0.0


def test_dataset_shape(ds):
    X, y, route_info, dates = ds
    assert isinstance(X, pd.DataFrame)
    assert isinstance(y, pd.Series)
    assert len(X) == len(y) == len(dates)


def test_features(ds):
    X, *_ = ds
    assert list(X.columns) == FEATURES


def test_no_nulls(ds):
    X, y, *_ = ds
    assert X.isnull().sum().sum() == 0
    assert y.isnull().sum() == 0


def test_target_range(ds):
    _, y, *_ = ds
    assert y.between(-10, 240).all()


def test_key_stations(ds):
    _, _, route_info, _ = ds
    for s in ["WEY", "SOU", "WOK"]:
        assert s in route_info.index


def test_no_data_leakage(ds):
    _, _, _, dates = ds
    years = pd.to_datetime(dates).dt.year
    assert set(years.unique()) == {2022, 2023, 2024, 2025}
    assert (years[years < 2025] < 2025).all()
