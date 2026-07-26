"""Generate a reproducible, clearly labelled synthetic used-car dataset."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "listings_synthetic.csv"

MODELS = {
    "BMW": {"3 Series": 44_000, "5 Series": 59_000, "X1": 43_000, "X3": 58_000, "i4": 61_000},
    "Audi": {"A3": 37_000, "A4": 45_000, "Q3": 44_000, "Q5": 60_000, "e-tron": 68_000},
    "Mercedes-Benz": {"A-Class": 38_000, "C-Class": 49_000, "E-Class": 64_000, "GLA": 45_000, "EQE": 72_000},
    "Volkswagen": {"Golf": 31_000, "Passat": 42_000, "Tiguan": 43_000, "ID.3": 40_000, "ID.4": 48_000},
    "Skoda": {"Octavia": 32_000, "Superb": 43_000, "Karoq": 35_000, "Kodiaq": 45_000, "Enyaq": 47_000},
}


def main(rows: int = 5_000, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    brands = np.array(list(MODELS))
    brand = rng.choice(brands, rows, p=[0.22, 0.20, 0.18, 0.25, 0.15])
    model = np.array([rng.choice(list(MODELS[b])) for b in brand])
    new_price = np.array([MODELS[b][m] for b, m in zip(brand, model)], dtype=float)

    age = np.clip(rng.gamma(2.2, 2.2, rows).round(), 0, 13).astype(int)
    mileage = np.maximum(1_500, age * rng.normal(15_500, 3_500, rows) + rng.normal(11_000, 8_000, rows)).round().astype(int)
    power = np.clip(rng.normal(145, 42, rows), 70, 360).round().astype(int)
    fuel = rng.choice(["Petrol", "Diesel", "Hybrid", "Electric"], rows, p=[0.38, 0.27, 0.18, 0.17])
    transmission = rng.choice(["Automatic", "Manual"], rows, p=[0.77, 0.23])
    country = rng.choice(["DE", "AT", "NL"], rows, p=[0.80, 0.12, 0.08])
    dealer = rng.choice(["Franchise dealer", "Independent dealer", "Private"], rows, p=[0.42, 0.40, 0.18])
    accident_free = rng.random(rows) > 0.10
    owners = np.clip((age / 3 + rng.normal(0.7, 0.7, rows)).round(), 1, 5).astype(int)
    days_market = np.clip(rng.gamma(2.3, 19, rows), 1, 180).round().astype(int)

    latest = pd.Timestamp("2026-06-30")
    listed_date = latest - pd.to_timedelta(rng.integers(0, 910, rows), unit="D")

    power_factor = 1 + (power - 145) * 0.0017
    age_factor = np.power(0.84, age)
    mileage_factor = np.exp(-mileage / 230_000)
    fuel_factor = pd.Series(fuel).map({"Petrol": 1.00, "Diesel": 0.96, "Hybrid": 1.07, "Electric": 1.05}).to_numpy()
    trans_factor = np.where(transmission == "Automatic", 1.045, 0.97)
    dealer_factor = pd.Series(dealer).map({"Franchise dealer": 1.055, "Independent dealer": 1.01, "Private": 0.95}).to_numpy()
    country_factor = pd.Series(country).map({"DE": 1.00, "AT": 1.035, "NL": 1.015}).to_numpy()
    history_factor = np.where(accident_free, 1.025, 0.86) * np.clip(1.02 - (owners - 1) * 0.018, 0.90, 1.03)
    seasonal = 1 + 0.018 * np.sin(2 * np.pi * listed_date.month.to_numpy() / 12)
    market_trend = 1 + ((listed_date - pd.Timestamp("2024-01-01")).days.to_numpy() / 365) * 0.014
    noise = rng.lognormal(mean=0, sigma=0.055, size=rows)

    fair_price = new_price * power_factor * age_factor * mileage_factor * fuel_factor * trans_factor
    fair_price *= dealer_factor * country_factor * history_factor * seasonal * market_trend * noise
    fair_price = np.clip(fair_price, 5_500, 105_000)

    pricing_bias = rng.normal(0.015, 0.055, rows) + np.where(days_market > 75, 0.025, 0)
    asking_price = np.maximum(4_900, fair_price * (1 + pricing_bias)).round(-1)

    df = pd.DataFrame(
        {
            "listing_id": [f"CAR-{i:05d}" for i in range(rows)],
            "listed_date": listed_date.strftime("%Y-%m-%d"),
            "country": country,
            "brand": brand,
            "model": model,
            "fuel": fuel,
            "transmission": transmission,
            "seller_type": dealer,
            "age_years": age,
            "mileage_km": mileage,
            "power_kw": power,
            "previous_owners": owners,
            "accident_free": accident_free,
            "days_on_market": days_market,
            "asking_price_eur": asking_price.astype(int),
        }
    ).sort_values("listed_date")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df):,} synthetic listings to {OUT}")


if __name__ == "__main__":
    main()
