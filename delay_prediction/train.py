import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from pipeline import make_dataset

OUT_DIR = Path(__file__).parent / "models"
OUT_DIR.mkdir(exist_ok=True)


def score(y_true, y_pred):
    return {
        "MAE":  round(mean_absolute_error(y_true, y_pred), 3),
        "RMSE": round(np.sqrt(mean_squared_error(y_true, y_pred)), 3),
        "R2":   round(r2_score(y_true, y_pred), 4),
    }


def run(direction="WEY2WAT", test_year=2025):
    print(f"Loading {direction} data...")
    X, y, route_info, dates = make_dataset(direction)

    years = pd.to_datetime(dates).dt.year
    X_tr, y_tr = X[years < test_year], y[years < test_year]
    X_te, y_te = X[years == test_year], y[years == test_year]
    print(f"  train={len(X_tr):,}  test={len(X_te):,}")

    candidates = {
        "Persistence (baseline)": None,
        "Ridge": make_pipeline(StandardScaler(), Ridge()),
        "kNN-10": make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=10, algorithm="kd_tree", n_jobs=-1)),
        "kNN-10 (weighted)": make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=10, algorithm="kd_tree", weights="distance", n_jobs=-1)),
        "Random Forest": RandomForestRegressor(n_estimators=30, max_depth=10, n_jobs=-1, random_state=42),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=30, max_depth=4, learning_rate=0.1, random_state=42),
    }

    results = {}
    trained = {}
    for name, model in candidates.items():
        if model is None:
            preds = X_te["delay_min"].values
        else:
            print(f"  Training {name}...", flush=True)
            model.fit(X_tr, y_tr)
            preds = model.predict(X_te)
            trained[name] = model
        results[name] = score(y_te, preds)

    table = pd.DataFrame(results).T
    print("\n" + table.to_string())

    best = min(trained, key=lambda n: results[n]["MAE"])
    print(f"\nBest model: {best}  (MAE={results[best]['MAE']} min)")

    joblib.dump(
        {
            "model": trained[best],
            "route_info": route_info,
            "name": best,
            "median_first_delay": float(X_tr["first_delay"].median()),
        },
        OUT_DIR / f"champion_{direction}.joblib",
    )
    table.to_csv(OUT_DIR / f"model_comparison_{direction}.csv")
    print(f"Saved champion_{direction}.joblib and model_comparison_{direction}.csv")


if __name__ == "__main__":
    run("WEY2WAT")
    run("WAT2WEY")
