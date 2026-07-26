"""Validate listings, train a time-aware pricing model and export dashboard data."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INPUT = DATA / "listings_synthetic.csv"
OUT_JS = ROOT / "dashboard" / "assets" / "dashboard-data.js"

NUMERIC = ["age_years", "mileage_km", "power_kw", "previous_owners", "days_on_market"]
CATEGORICAL = ["country", "brand", "model", "fuel", "transmission", "seller_type", "accident_free"]
TARGET = "asking_price_eur"


def validate(df: pd.DataFrame) -> dict[str, int]:
    required = {"listing_id", "listed_date", TARGET, *NUMERIC, *CATEGORICAL}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    checks = {
        "duplicate_listing_ids": int(df["listing_id"].duplicated().sum()),
        "null_required_cells": int(df[list(required)].isna().sum().sum()),
        "nonpositive_prices": int((df[TARGET] <= 0).sum()),
        "negative_mileage": int((df["mileage_km"] < 0).sum()),
        "invalid_age": int((~df["age_years"].between(0, 30)).sum()),
    }
    if any(checks.values()):
        raise ValueError(f"Data-quality checks failed: {checks}")
    return checks


def design_matrices(train: pd.DataFrame, test: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Build a train-owned feature space without requiring an external ML runtime."""
    def enrich(frame: pd.DataFrame) -> pd.DataFrame:
        x = frame[NUMERIC + CATEGORICAL].copy()
        x["age_squared"] = x["age_years"] ** 2
        x["log_mileage"] = np.log1p(x["mileage_km"])
        x["power_squared"] = x["power_kw"] ** 2
        for c in CATEGORICAL:
            x[c] = x[c].astype(str)
        return x

    a, b = enrich(train), enrich(test)
    numeric = NUMERIC + ["age_squared", "log_mileage", "power_squared"]
    mean, std = a[numeric].mean(), a[numeric].std().replace(0, 1)
    a[numeric] = (a[numeric] - mean) / std
    b[numeric] = (b[numeric] - mean) / std
    a = pd.get_dummies(a, columns=CATEGORICAL, drop_first=False, dtype=float)
    b = pd.get_dummies(b, columns=CATEGORICAL, drop_first=False, dtype=float).reindex(columns=a.columns, fill_value=0)
    return np.c_[np.ones(len(a)), a.to_numpy(float)], np.c_[np.ones(len(b)), b.to_numpy(float)]


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float = 7.5) -> np.ndarray:
    penalty = np.eye(x.shape[1]) * alpha
    penalty[0, 0] = 0
    return np.linalg.solve(x.T @ x + penalty, x.T @ y)


def mae(y: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y - pred)))


def mape(y: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs((y - pred) / np.clip(y, 1, None))))


def r2(y: np.ndarray, pred: np.ndarray) -> float:
    return float(1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2))


def main() -> dict:
    if not INPUT.exists():
        from generate_data import main as generate

        generate()
    df = pd.read_csv(INPUT, parse_dates=["listed_date"]).sort_values("listed_date").reset_index(drop=True)
    quality = validate(df)
    cut = int(len(df) * 0.80)
    train, test = df.iloc[:cut].copy(), df.iloc[cut:].copy()
    y_train, y_test = train[TARGET].to_numpy(float), test[TARGET].to_numpy(float)
    x_train, x_test = design_matrices(train, test)
    beta = fit_ridge(x_train, np.log1p(y_train))
    train_pred = np.expm1(x_train @ beta)
    pred = np.expm1(x_test @ beta)
    baseline_table = train.groupby(["model", "age_years"])[TARGET].median()
    baseline_index = pd.MultiIndex.from_frame(test[["model", "age_years"]])
    baseline_pred = baseline_table.reindex(baseline_index).to_numpy(float)
    baseline_pred = np.where(np.isnan(baseline_pred), np.median(y_train), baseline_pred)
    relative_residual = (y_train - train_pred) / np.clip(train_pred, 1, None)
    residual_p10, residual_p90 = np.quantile(relative_residual, [0.10, 0.90])
    p10 = pred * (1 + residual_p10)
    p90 = pred * (1 + residual_p90)

    test["model_price_eur"] = np.round(pred).astype(int)
    test["price_p10_eur"] = np.round(p10).astype(int)
    test["price_p90_eur"] = np.round(p90).astype(int)
    test["price_gap_pct"] = ((test[TARGET] - test["model_price_eur"]) / test["model_price_eur"] * 100).round(1)
    test["recommended_action"] = np.select(
        [
            (test["days_on_market"] > 45) & (test["price_gap_pct"] > 5),
            test["price_gap_pct"] < -8,
        ],
        ["Review markdown", "Check underpricing"],
        default="Hold",
    )
    test.to_csv(DATA / "scored_listings.csv", index=False)

    model_mae = mae(y_test, pred)
    baseline_mae = mae(y_test, baseline_pred)
    summary = {
        "as_of": str(df["listed_date"].max().date()),
        "data_label": "Synthetic demo data",
        "train_rows": len(train),
        "test_rows": len(test),
        "mae_eur": round(model_mae),
        "mape_pct": round(mape(y_test, pred) * 100, 1),
        "r2": round(r2(y_test, pred), 3),
        "baseline_mae_eur": round(float(baseline_mae)),
        "baseline_improvement_pct": round(float((baseline_mae - model_mae) / baseline_mae * 100), 1),
        "action_candidates": int((test["recommended_action"] == "Review markdown").sum()),
        "quality_checks_passed": len(quality),
    }

    by_brand = (
        test.groupby("brand")
        .agg(listings=("listing_id", "size"), median_asking=("asking_price_eur", "median"), median_model=("model_price_eur", "median"), mae=("asking_price_eur", lambda s: 0))
        .reset_index()
    )
    by_brand["mae"] = test.groupby("brand").apply(
        lambda x: np.mean(np.abs(x["asking_price_eur"] - x["model_price_eur"])), include_groups=False
    ).to_numpy()

    by_age = (
        test.groupby("age_years")
        .agg(listings=("listing_id", "size"), asking=("asking_price_eur", "median"), model=("model_price_eur", "median"))
        .reset_index()
        .query("listings >= 8")
    )

    inventory = (
        test.sort_values(["recommended_action", "days_on_market", "price_gap_pct"], ascending=[True, False, False])
        .loc[:, ["listing_id", "brand", "model", "age_years", "mileage_km", "days_on_market", "asking_price_eur", "model_price_eur", "price_gap_pct", "recommended_action"]]
        .head(45)
    )

    payload = {
        "summary": summary,
        "byBrand": json.loads(by_brand.round(1).to_json(orient="records")),
        "byAge": json.loads(by_age.round(1).to_json(orient="records")),
        "inventory": json.loads(inventory.to_json(orient="records")),
    }
    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUT_JS.write_text("window.DASHBOARD_DATA = " + json.dumps(payload, indent=2) + ";\n", encoding="utf-8")
    (DATA / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return payload


if __name__ == "__main__":
    main()
