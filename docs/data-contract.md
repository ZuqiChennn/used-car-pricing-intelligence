# Data contract

One row represents one observed listing at its listing date.

| Field | Type | Definition |
|---|---|---|
| `listing_id` | string | Stable unique listing identifier |
| `listed_date` | date | Date the listing entered the observed inventory |
| `country` | category | ISO country code |
| `brand`, `model` | category | Vehicle make and model family |
| `fuel`, `transmission` | category | Powertrain and transmission |
| `seller_type` | category | Franchise dealer, independent dealer or private |
| `age_years` | integer | Whole years since first registration |
| `mileage_km` | integer | Odometer reading in kilometres |
| `power_kw` | integer | Rated power |
| `previous_owners` | integer | Reported previous owners |
| `accident_free` | boolean | Reported accident-free status |
| `days_on_market` | integer | Days active at snapshot |
| `asking_price_eur` | number | Current advertised price, VAT treatment source-dependent |

Real-data adapters must preserve a source timestamp, currency conversion method, deletion policy and licence. Transaction prices must not be silently mixed with asking prices.
