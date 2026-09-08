# Canonical ET collection dictionary

Generated from `CanonicalET`; do not maintain a conflicting field list by hand.

Input source: explicitly mapped CSV column or manual observation. Original CSV is retained; edits receive attributable audit entries. Empty optional values remain null. No biological measurements or outcomes are imputed.

| Field | Required | Type / unit | Allowed values / range |
|---|---|---|---|
| et_number | Yes | integer  | > 0 |
| et_date | Yes | string YYYY-MM-DD | Nullable when optional; finite numbers only |
| recipient_tag | Yes | string  | min characters 1; max characters 50 |
| farm_location | Yes | string  | min characters 1; max characters 200 |
| donor_tag | No | string  | max characters 50 |
| sire_name | No | string  | max characters 100 |
| embryo_stage | Yes | integer  | ≥ 4; ≤ 8 |
| embryo_grade | Yes | integer  | ≥ 1; ≤ 4 |
| fresh_or_frozen | No | string  | Fresh, Frozen |
| bc_score | No | number 1–5 scale | ≥ 1; ≤ 5 |
| cl_measure_mm | No | number mm | ≥ 0; ≤ 50 |
| cl_side | No | string  | Left, Right |
| pc1_date | No | string YYYY-MM-DD | Nullable when optional; finite numbers only |
| pc1_result | No | string  | Pregnant, Open, Recheck |
| recipient_breed | No | string  | max characters 100 |
| recipient_age_years | No | number years | ≥ 0 |
| recipient_parity | No | integer  | ≥ 0 |
| cow_or_heifer | No | string  | Cow, Heifer |
| previous_et_count | No | integer  | ≥ 0 |
| previous_et_pregnancies | No | integer  | ≥ 0 |
| previous_et_failures | No | integer  | ≥ 0 |
| prior_pregnancy_loss | No | boolean  | Nullable when optional; finite numbers only |
| donor_breed | No | string  | max characters 100 |
| donor_age_years | No | number years | ≥ 0 |
| donor_parity | No | integer  | ≥ 0 |
| donor_bcs | No | number 1–5 scale | ≥ 1; ≤ 5 |
| sire_breed | No | string  | max characters 100 |
| semen_type | No | string  | Conventional, Sexed, Unknown |
| semen_batch | No | string  | max characters 100 |
| embryo_identifier | No | string  | max characters 100 |
| embryo_day | No | integer days | ≥ 1 |
| production_method | No | string  | IVF, MOET, Other |
| cryopreservation_method | No | string  | max characters 100 |
| freezing_date | No | string YYYY-MM-DD | Nullable when optional; finite numbers only |
| opu_date | No | string YYYY-MM-DD | Nullable when optional; finite numbers only |
| ivf_date | No | string YYYY-MM-DD | Nullable when optional; finite numbers only |
| culture_media | No | string  | max characters 100 |
| protocol_name | No | string  | max characters 100 |
| technician_name | No | string  | max characters 100 |
| p4_ng_ml | No | number ng/mL | ≥ 0 |
| cl_quality | No | string  | max characters 100 |
| estrus_date | No | string YYYY-MM-DD | Nullable when optional; finite numbers only |
| estrus_type | No | string  | max characters 100 |
| days_estrus_to_et | No | number days | ≥ 0 |
| heat_observed | No | boolean  | Nullable when optional; finite numbers only |
| transfer_side | No | string  | Left, Right |
| transfer_location | No | string  | max characters 100 |
| transfer_difficulty | No | string  | max characters 100 |
| season | No | string  | max characters 50 |
| ambient_temperature_c | No | number °C | ≥ -50; ≤ 60 |
| relative_humidity_pct | No | number % | ≥ 0; ≤ 100 |
| pc2_date | No | string YYYY-MM-DD | Nullable when optional; finite numbers only |
| pc2_result | No | string  | Pregnant, Open, Recheck |
| pregnancy_loss | No | boolean  | Nullable when optional; finite numbers only |
| pregnancy_loss_date | No | string YYYY-MM-DD | Nullable when optional; finite numbers only |
| calving_date | No | string YYYY-MM-DD | Nullable when optional; finite numbers only |
| calving_outcome | No | string  | max characters 100 |
| notes | No | string  | max characters 5000 |

Category normalization: case-insensitive fresh/frozen, CL/transfer side, cow/heifer and semen category. P/positive becomes Pregnant, O/negative becomes Open, Pending becomes Recheck. Dates use ISO format. Source strings are trimmed; source CSV text is preserved.

Cross-field validation: resolved pregnancy outcomes require checkpoint dates; checkpoints follow transfer and one another; OPU/IVF/freezing/estrus precede transfer; IVF follows OPU; freezing follows IVF; estrus interval agrees with dates when both are provided; previous ET successes plus failures cannot exceed previous ET count; recorded pregnancy loss requires its loss flag; loss/calving cannot precede transfer.

Ranges are implementation checks, not treatment recommendations. Unbounded positive measures require local domain review for plausibility. Source provenance includes source_type, source_reference, uploader, SHA-256, mapping, CSV row and schema version in the release documentation. Synthetic batches remain in staging and never create clinical records through canonical intake.
