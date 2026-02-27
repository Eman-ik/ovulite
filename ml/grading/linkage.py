"""Image-to-record linkage (ROADMAP task 3.2).

Maps blq{N}.jpg filenames to embryo records in the database.
Since the CSV dataset has 488 ET records and there are 482 images,
we use a sequential mapping: image N → ET record N (by et_number).

This module also provides helpers for building labelled datasets
by joining image paths with embryo metadata from the DB or CSV.
"""

import re
from pathlib import Path

import pandas as pd

from .config import IMAGE_DIR


def discover_images(image_dir: Path | None = None) -> list[dict]:
    """Discover all embryo images and extract their sequence numbers.

    Returns list of dicts with keys: path, filename, sequence_number
    """
    img_dir = image_dir or IMAGE_DIR
    images = []
    for p in sorted(img_dir.glob("blq*.jpg")):
        match = re.match(r"blq(\d+)\.jpg", p.name, re.IGNORECASE)
        if match:
            images.append({
                "path": str(p),
                "filename": p.name,
                "sequence_number": int(match.group(1)),
            })
    return images


def build_image_record_mapping(
    image_dir: Path | None = None,
    et_csv_path: str | None = None,
) -> pd.DataFrame:
    """Build a mapping DataFrame linking images to ET records.

    The mapping uses sequential number: blq{N}.jpg → row N in the ET data.
    Since images have NO ground-truth labels, we use the `Embryo Grade`
    column from the CSV as a proxy label (caveat: 482/488 are Grade 1).

    Returns DataFrame with columns:
        image_path, sequence_number, et_number, embryo_stage, embryo_grade,
        donor_breed, fresh_or_frozen, technician_name, pregnancy_outcome
    """
    images = discover_images(image_dir)
    img_df = pd.DataFrame(images)

    # Load ET data for metadata
    if et_csv_path:
        et_df = pd.read_csv(et_csv_path, dtype=str)
    else:
        from ml.config import DATA_CSV
        et_df = pd.read_csv(str(DATA_CSV), dtype=str)

    et_df = et_df.dropna(how="all").reset_index(drop=True)

    # Create a sequence_number column from row index (1-based to match blq numbering)
    et_df["sequence_number"] = et_df.index + 1

    # Clean relevant columns
    def _clean(val):
        if pd.isna(val) or str(val).strip() in (".", "", "nan"):
            return None
        return str(val).strip()

    records = []
    for _, row in et_df.iterrows():
        records.append({
            "sequence_number": row["sequence_number"],
            "et_number": _clean(row.get("# ET")),
            "embryo_stage": _clean(row.get("Embryo Stage 4-8")),
            "embryo_grade": _clean(row.get("Embryo Grade")),
            "donor_breed": _clean(row.get("Donor Breed")),
            "fresh_or_frozen": _clean(row.get("Fresh or Frozen")),
            "technician_name": _clean(row.get("ET Tech")),
            "pc1_result": _clean(row.get("1st PC Result")),
        })

    record_df = pd.DataFrame(records)

    # Merge images with records
    merged = img_df.merge(record_df, on="sequence_number", how="inner")

    return merged


def build_grade_labels(mapping_df: pd.DataFrame) -> tuple[list[Path], list[int], list[dict]]:
    """Extract image paths, grade labels, and metadata from the mapping.

    Since embryo grades are nearly constant (482/488 Grade 1), we create
    a 3-class pseudo-label based on pregnancy outcome for more useful training:
    - Class 0: "Low viability" (Open outcome + Grade ≥ 2)
    - Class 1: "Medium viability" (Open outcome + Grade 1)
    - Class 2: "High viability" (Pregnant outcome)

    Returns
    -------
    image_paths : list of Path objects
    labels : list of int (0, 1, 2)
    metadata_dicts : list of metadata dicts for fusion branch
    """
    paths = []
    labels = []
    meta = []

    for _, row in mapping_df.iterrows():
        pc1 = row.get("pc1_result")
        grade = row.get("embryo_grade")

        # Skip rows without outcome (can't create label)
        if pc1 not in ("Pregnant", "Open"):
            continue

        grade_int = int(grade) if grade and grade.isdigit() else 1

        if pc1 == "Pregnant":
            label = 2  # High viability
        elif grade_int >= 2:
            label = 0  # Low viability
        else:
            label = 1  # Medium viability (Open + Grade 1)

        paths.append(Path(row["path"]))
        labels.append(label)

        metadata_dict = {
            "embryo_stage": float(row["embryo_stage"]) if row.get("embryo_stage") else 6.0,
            "embryo_grade": float(grade_int),
            "donor_breed": str(row.get("donor_breed", "Unknown") or "Unknown"),
            "fresh_or_frozen": str(row.get("fresh_or_frozen", "Fresh") or "Fresh"),
            "technician_name": str(row.get("technician_name", "Unknown") or "Unknown"),
        }
        meta.append(metadata_dict)

    return paths, labels, meta
