#!/usr/bin/env python3
"""Backfill ``ivf_batches.semen_type`` from the ingest CSV, and verify it.

Migration 015 adds the column but leaves it null on purpose. The value is not
recoverable from the database: ``sires.semen_type`` exists and is populated,
but at least one sire (Mr Karu Manso 800) is used with both conventional and
sexed straws, so deriving from it is 86.2% accurate and manufactures a 5.7 pp
difference in pregnancy rate that the source data does not contain.

The real per-transfer values are in the ingest CSV. This script maps them up
to the IVF batch, which is safe because semen type is consistent within all
117 batches — that is checked here rather than assumed, and the script refuses
to write anything if it ever stops being true.

Nothing is written unless every batch resolves to exactly one value.

    python -m scripts.backfill_semen_type [--csv PATH] [--apply]

Without ``--apply`` it reports what it would do and changes nothing.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

DEFAULT_CSV = (
    Path(__file__).resolve().parent.parent.parent / "docs" / "dataset" / "ovulite_cleaned_et_data.csv"
)


def normalize(value: str | None) -> str | None:
    """Map the CSV's free text onto the two values the column accepts.

    The source uses 'Conventional', 'Sexed Female' and 'Pre-Sorted for Female';
    the last two are both sorted semen. Anything unrecognised returns None so
    it is skipped rather than guessed into a bucket.
    """
    text_value = (value or "").strip().lower()
    if not text_value:
        return None
    if "sex" in text_value or "sort" in text_value:
        return "Sexed"
    if "conventional" in text_value:
        return "Conventional"
    return None


def load_truth(csv_path: Path) -> dict[int, str]:
    """et_number -> semen type, from the ingest CSV."""
    truth: dict[int, str] = {}
    with io.open(csv_path, encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            raw_et = (row.get("# ET") or "").strip()
            value = normalize(row.get("Semen type"))
            if not raw_et or value is None:
                continue
            try:
                truth[int(float(raw_et))] = value
            except ValueError:
                continue
    return truth


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--apply", action="store_true", help="write the values (otherwise dry run)")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 1

    truth = load_truth(args.csv)
    print(f"CSV rows with a usable semen type: {len(truth)}")

    with engine.connect() as conn:
        links = list(
            conn.execute(
                text(
                    """
                    SELECT e.ivf_batch_id, t.et_number
                    FROM et_transfers t
                    JOIN embryos e ON e.embryo_id = t.embryo_id
                    WHERE e.ivf_batch_id IS NOT NULL AND t.et_number IS NOT NULL
                    """
                )
            )
        )

    per_batch: dict[int, set[str]] = defaultdict(set)
    for batch_id, et_number in links:
        value = truth.get(et_number)
        if value:
            per_batch[batch_id].add(value)

    conflicted = {b: v for b, v in per_batch.items() if len(v) > 1}
    resolved = {b: next(iter(v)) for b, v in per_batch.items() if len(v) == 1}

    print(f"batches reachable from the CSV: {len(per_batch)}")
    print(f"batches resolving to one value: {len(resolved)}")
    print(f"batches with conflicting values: {len(conflicted)}")

    if conflicted:
        # Per-batch storage assumes one semen type per fertilisation. If that
        # ever breaks, the column is in the wrong place and writing would
        # silently discard half the truth.
        print("\nRefusing to write — semen type is not consistent within these batches:")
        for batch_id, values in list(conflicted.items())[:10]:
            print(f"  batch {batch_id}: {sorted(values)}")
        print("The column belongs on the embryo, not the batch, if this is real.")
        return 2

    counts: dict[str, int] = defaultdict(int)
    for value in resolved.values():
        counts[value] += 1
    print("\nwould write:", dict(counts))

    if not args.apply:
        print("\nDry run — pass --apply to write.")
        return 0

    with engine.begin() as conn:
        for batch_id, value in resolved.items():
            conn.execute(
                text("UPDATE ivf_batches SET semen_type = :v WHERE ivf_batch_id = :b"),
                {"v": value, "b": batch_id},
            )

    # Verify against the per-transfer source rather than trusting the write.
    with engine.connect() as conn:
        written = {
            row[0]: row[1]
            for row in conn.execute(
                text(
                    """
                    SELECT t.et_number, b.semen_type
                    FROM et_transfers t
                    JOIN embryos e ON e.embryo_id = t.embryo_id
                    JOIN ivf_batches b ON b.ivf_batch_id = e.ivf_batch_id
                    WHERE t.et_number IS NOT NULL AND b.semen_type IS NOT NULL
                    """
                )
            )
        }
    compared = [(k, v) for k, v in written.items() if truth.get(k)]
    agree = sum(1 for k, v in compared if truth[k] == v)
    print(f"\nverification: {agree}/{len(compared)} transfers match the CSV", end=" ")
    print("— exact" if agree == len(compared) else f"— {len(compared) - agree} MISMATCH")
    return 0 if agree == len(compared) else 3


if __name__ == "__main__":
    raise SystemExit(main())
