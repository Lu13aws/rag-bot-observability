-- Acceptance check for S2.3.1. Expected: 2 rows (model-small, model-large)
-- with the fictional prices from sample-data/model_pricing.csv.
SELECT model_id, price_in_per_1k, price_out_per_1k, valid_from
FROM model_pricing
ORDER BY model_id
