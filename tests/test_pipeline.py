from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline import main, validate


class PipelineTests(unittest.TestCase):
    def test_data_contract(self):
        df = pd.read_csv(ROOT / "data" / "listings_synthetic.csv")
        self.assertEqual(validate(df), {
            "duplicate_listing_ids": 0,
            "null_required_cells": 0,
            "nonpositive_prices": 0,
            "negative_mileage": 0,
            "invalid_age": 0,
        })

    def test_model_beats_baseline(self):
        result = main()["summary"]
        self.assertLess(result["mae_eur"], result["baseline_mae_eur"])
        self.assertGreater(result["baseline_improvement_pct"], 15)
        self.assertTrue(0 < result["mape_pct"] < 25)

    def test_scored_output_is_complete(self):
        scored = pd.read_csv(ROOT / "data" / "scored_listings.csv")
        self.assertTrue(scored["model_price_eur"].gt(0).all())
        self.assertTrue(scored["price_p90_eur"].ge(scored["price_p10_eur"]).all())
        self.assertLessEqual(set(scored["recommended_action"]), {"Hold", "Review markdown", "Check underpricing"})


if __name__ == "__main__":
    unittest.main()
