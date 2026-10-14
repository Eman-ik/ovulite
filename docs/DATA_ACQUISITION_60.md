# Data acquisition handover — 60% release

Reviewed 2026-09-08. These are discovery records, not imported training data. No dataset below was converted into invented individual transfers. Counts refer to the described studies, not verified downloadable row counts.

| Source | Size and variables described | Outcome and fit | Rights / next action |
|---|---|---|---|
| [Gimeno et al., metabolic signature](https://zenodo.org/records/5647993) | 28 fresh + 58 frozen/thawed ETs; culture metabolites, embryo stage, cryopreservation and sire variation | Bovine pregnancy and birth; relevant source for an anonymized ET-data request | CC BY 4.0 applies to the available article. Repository lists a PDF, not a verified row-level data table. Request underlying de-identified rows and explicit data-use terms from the corresponding research group. |
| [Late embryonic losses](https://data.mendeley.com/datasets/htd46gmpgr/1) | 92 cows, 46 loss and 46 controls; infection status, progesterone, parity and ultrasound definition | Post-AI loss at 28–42 days; a different endpoint/population from pregnancy after ET | Landing-page description identified; file-level license and rows not verified. Keep separate from ET training; inspect source rights before acquisition. |
| [Long-term metabolic and developmental effects](https://data.mendeley.com/datasets/kchnt9vxhm/1) | Supplementary growth, IGF2 and metabolic measurements; sample count not verified | Offspring after AI and fresh/frozen/vitrified ET; useful for future follow-up research, not a ready ET-success cohort | Repository states CC BY 4.0. Review individual supplementary files and linkage before considering intake. |
| [Holstein recipient fertility supplement](https://data.mendeley.com/datasets/yfkj4g62nv/2) | Factorial trial summary of synchronization and rbST effects; row count not stated | Fresh IVF recipient fertility; available description is a P-value table, not individual outcomes | Repository states CC BY 4.0. Request individual anonymized records if a legitimate collaboration is established. |

## Ready-to-adapt outreach draft — not sent

Subject: Academic request for anonymized bovine embryo-transfer data — OVULITE

Dear corresponding author / research collaboration team,

I am developing OVULITE, an academic bovine reproduction data-management and decision-support project. Your work on [study title] is relevant to our prospective canonical ET schema. Would your group consider sharing an anonymized retrospective dataset, or discussing a research collaboration?

Where available, we would request one row per embryo transfer with pseudonymous donor, embryo and recipient identifiers; transfer date or a consistently shifted date; embryo stage/grade and fresh/frozen status; recipient and synchronization metadata; and dated pregnancy outcomes. Optional fields are documented in the attached canonical dictionary. Missing measurements would remain missing. We would not require owner names, contact details, precise farm coordinates or direct personal identifiers.

Before transfer, we would agree on permitted use, attribution, access, retention and publication terms, and any institutional approvals. We can provide a mapping template, validation report and secure transfer arrangement appropriate to your requirements. We would keep study sources distinguishable and would not represent synthetic examples as real observations.

Thank you for considering the request.

[Researcher's name, institution, supervisor and contact details]

## Prospective collection package

Use the Data Intake page's downloadable CSV template and [canonical dictionary](CANONICAL_ET_DICTIONARY.md). Assign stable pseudonymous identifiers, record the source reference, retain original units until explicitly harmonized, and enter dated outcome follow-ups. Preview validation and missingness before commit. Never infer a pregnancy result from an absent checkpoint. The release provides collection tooling; it does not assert that a target real-data cohort has been acquired.
