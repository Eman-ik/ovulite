"""Generate the collection dictionary from the implemented validation schema."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from app.services.canonical_intake import CanonicalET

schema = CanonicalET.model_json_schema()
rows = ["# Canonical ET collection dictionary", "", "Generated from `CanonicalET`; do not maintain a conflicting field list by hand.", "",
        "Input source: explicitly mapped CSV column or manual observation. Original CSV is retained; edits receive attributable audit entries. Empty optional values remain null. No biological measurements or outcomes are imputed.", "",
        "| Field | Required | Type / unit | Allowed values / range |", "|---|---|---|---|"]
for key, definition in schema["properties"].items():
    field = next((item for item in definition.get("anyOf", []) if item.get("type") != "null"), definition)
    unit = "years" if key.endswith("_years") else "mm" if key.endswith("_mm") else "ng/mL" if key == "p4_ng_ml" else "°C" if key.endswith("_c") else "%" if key.endswith("_pct") else "1–5 scale" if key in {"bc_score", "donor_bcs"} else "days" if key in {"embryo_day", "days_estrus_to_et"} else "YYYY-MM-DD" if field.get("format") == "date" else ""
    limits = ", ".join(map(str, field.get("enum", [])))
    if not limits:
        limits = "; ".join(f"{label} {field[name]}" for name, label in (("minimum", "≥"), ("maximum", "≤"), ("exclusiveMinimum", ">"), ("minLength", "min characters"), ("maxLength", "max characters")) if name in field) or "Nullable when optional; finite numbers only"
    rows.append(f"| {key} | {'Yes' if key in schema['required'] else 'No'} | {field.get('type', '')} {unit} | {limits} |")
rows += ["", "Category normalization: case-insensitive fresh/frozen, CL/transfer side, cow/heifer and semen category. P/positive becomes Pregnant, O/negative becomes Open, Pending becomes Recheck. Dates use ISO format. Source strings are trimmed; source CSV text is preserved.", "", "Cross-field validation: resolved pregnancy outcomes require checkpoint dates; checkpoints follow transfer and one another; OPU/IVF/freezing/estrus precede transfer; IVF follows OPU; freezing follows IVF; estrus interval agrees with dates when both are provided; previous ET successes plus failures cannot exceed previous ET count; recorded pregnancy loss requires its loss flag; loss/calving cannot precede transfer.", "", "Ranges are implementation checks, not treatment recommendations. Unbounded positive measures require local domain review for plausibility. Source provenance includes source_type, source_reference, uploader, SHA-256, mapping, CSV row and schema version in the release documentation. Synthetic batches remain in staging and never create clinical records through canonical intake."]
destination = BASE.parent / "docs" / "CANONICAL_ET_DICTIONARY.md"
destination.write_text("\n".join(rows) + "\n", encoding="utf-8")
(BASE / "resources" / "canonical_et_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
print(f"Exported {len(schema['properties'])} fields to {destination}")
