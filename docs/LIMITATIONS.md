# Ovulite — System Limitations & Confidence Boundaries

> **Document Purpose:** Transparent disclosure of what the system cannot do,
> statistical limitations, and boundaries where predictions should not be trusted.

---

## 1. Data Limitations

### Sample Size
- **488 ET records** total — an ultra-small dataset for ML
- GroupKFold cross-validation with only ~5 folds means wide confidence intervals
- Bootstrap CI (n=200) provides uncertainty estimates but cannot compensate for small N
- Rare events (e.g., protocol × breed interactions) have insufficient power

### Class Imbalance
- **~71% Open, ~29% Pregnant** in PC1 results
- `class_weight=balanced` mitigates training bias but does not create new signal
- PR-AUC preferred over ROC-AUC for evaluation

### Missing Data
- **BC Score**: ~77.5% missing — `bc_missing` flag used as imputation surrogate
- **Embryo Grade**: Near-zero variance in the dataset — limited predictive value
- **Sire BW EPD**: Partially available; imputed with median
- **Heat Day**: Some records missing; imputed with mode

### Temporal Coverage
- Data spans a limited time window; seasonal/yearly effects may be confounded
- Holdout set (Dec 2025+) may have shifted distributions

---

## 2. Model Limitations

### Pregnancy Prediction
- **Calibration**: Isotonic calibration post-hoc; still may be poorly calibrated on out-of-distribution inputs
- **TabPFN**: Works well on small tabular data but is a black-box prior-fitted network — interpretability is limited to post-hoc SHAP
- **Generalization**: Model trained on data from specific farms/clients — may not transfer to different geographic regions, breeds, or lab protocols
- **Feature Leakage**: PC results, days_in_pregnancy, and other post-transfer columns are excluded, but any feature correlated with these could introduce subtle leakage
- **No causal claims**: All relationships are correlational; the system cannot recommend interventions

### Embryo Grading
- **No ground-truth labels**: Pseudo-labels derived from pregnancy outcomes, not embryologist consensus
- **3 classes** (High/Medium/Low) are proxy categories, not established embryo quality standards
- **SimCLR pretraining** improves representation but does not guarantee biologically meaningful features
- **Grad-CAM** highlights regions of interest but may not correspond to known morphological markers
- **482 images** is far below typical computer vision dataset sizes

### QC Anomaly Detection
- **Isolation Forest** is unsupervised — it detects statistical outliers, not necessarily quality problems
- **EWMA/CUSUM** assume approximate normality of monthly metrics
- **Contamination=0.15** is a subjective choice; tuning requires domain expert validation
- **Alert severity** thresholds are heuristic, not clinically validated

---

## 3. System Boundaries — When NOT to Trust Predictions

| Scenario | Why |
|----------|-----|
| New protocol never seen in training data | No signal; model defaults to prior |
| Donor breed not in training set | Breed encoding will be novel; prediction unreliable |
| CL measure < 10mm or > 40mm | Outside observed distribution — extrapolation |
| BC Score submitted when historically missing | Model trained with bc_missing flag; providing a value changes feature semantics |
| Transfers > 6 months after training data ends | Temporal drift likely; re-training recommended |
| Single-embryo donor with no history | No donor-level signal available |

---

## 4. Ethical & Practical Considerations

- **Not a substitute for veterinary judgment** — the system is a decision-support tool
- **Bias amplification**: If historical data reflects biased practices, the model will learn them
- **Technician analytics**: Performance comparisons must be interpreted carefully; confounding variables (assigned animal quality, season, protocol) affect outcomes
- **Protocol recommendations**: The system identifies correlations, not causal effects; A/B testing or randomized trials would be needed for true protocol comparison
- **Data privacy**: All donor/sire IDs, farm locations, and client identifiers must be handled per data protection policies

---

## 5. Recommended Safeguards

1. **Always show confidence intervals** alongside point predictions
2. **Flag out-of-distribution inputs** before showing predictions
3. **Re-train quarterly** as new data accumulates (target: every 100 new records)
4. **Monitor calibration** via the model monitoring dashboard
5. **Domain expert review** of QC alerts before operational decisions
6. **Document all model updates** in a version-controlled model registry
