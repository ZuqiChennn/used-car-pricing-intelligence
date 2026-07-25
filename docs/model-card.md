# Model card

## Intended use

Decision support for market-price review and inventory triage. The model is not intended to autonomously set a binding customer price.

## Evaluation design

Listings are sorted by `listed_date`; the earliest 80% form the training set and the latest 20% form the holdout. This approximates deployment on future listings and avoids look-ahead leakage.

## Model

A regularized log-price regression receives standardized numeric attributes, selected non-linear transforms and one-hot-encoded categorical attributes. A model-and-age median estimator is retained as the benchmark. P10/P90 bands apply empirical relative training-residual quantiles to each estimate.

## Risks

- Asking prices do not equal transaction prices.
- Synthetic demo performance is not evidence of real-market performance.
- Sparse models, trims and option packages can have wider error.
- Seller behaviour and local negotiation are not fully observed.
- The empirical residual band is not a calibrated causal confidence interval.

## Monitoring

Track MAE and MAPE by brand, vehicle age, country and price band; unknown-category rate; missingness; prediction-band coverage; and distribution drift in mileage, age and fuel mix.
