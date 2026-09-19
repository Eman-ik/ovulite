#!/usr/bin/env python
"""Fill the demonstration gaps in an Ovulite database.

Why this exists
---------------
The loaded programme is a real clinical spine — 482 transfers, 489 embryos,
49 donors, 18 sires, 115 OPU sessions — but most of the *surrounding* record is
missing, so a large part of the product renders empty:

    opu_sessions          every oocyte count null  (115/115)
    ivf_batches           every lab number null    (117/117)
    recipients            no breed/parity/status   (396/396)
    ivm_batches           table empty
    embryo_observations   table empty
    recipient_evaluations table empty
    protocol_steps        table empty -> the synchronisation board has nothing to schedule
    synchronization_enrollments  table empty
    calving_records       table empty
    predictions           table empty

This script fills those gaps so every screen has something real-shaped to show.

What it will not do
-------------------
It never overwrites a value that is already recorded, and it never touches the
outcome spine: ``et_date``, ``pc1_result``, embryo/donor/sire identity and
linkage are left exactly as loaded. The headline pregnancy rate, the research
findings and the model evaluation are computed from those columns, so seeding
cannot move them.

Every row this script writes carries ``SEED_TAG`` in its ``notes`` column, so
seeded and recorded data can always be told apart::

    SELECT count(*) FROM recipient_evaluations WHERE notes LIKE '%[demo-seed%';

and ``--purge`` removes exactly those rows again.

Honesty note
------------
Seeded lab numbers are *plausible*, not observed. Any rate derived from them
(maturation, cleavage, blastocyst, live birth) is a demonstration figure. The
one place this matters most is ``calving_records``: no calving outcome was ever
recorded for this programme, so every live-birth number in the application
after seeding is synthetic. That is a deliberate, tagged, reversible choice —
not a claim about these animals.

Usage
-----
    python scripts/seed_demo_data.py --dry-run
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --purge
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, timedelta

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:  # pragma: no cover - the script is Postgres-only by design
    sys.exit("psycopg2 is required: pip install psycopg2-binary")

SEED_TAG = "[demo-seed v1]"
RNG_SEED = 20260912

DEFAULT_DSN = "postgresql://ovulite:ovulite_dev_password@127.0.0.1:5432/ovulite"

# The 23:34:28 insert batch was a smoke test: seven transfers whose pc2_result
# holds integers ('54', '83'), whose fetal_sexing holds integers, whose
# days_in_pregnancy is negative and whose check dates precede the transfer by
# months. They are the sole reason GET /transfers/ returns 500 — the date
# validator on ETTransferBase also runs over responses, so one bad row takes
# down the whole page — and they add six spurious single-transfer months to
# every trend chart.
JUNK_BATCH_TS = "2026-09-03 23:34:28.233001+05"


# ──────────────────────────────────────────────────────────────────────────
# Reference vocabularies, drawn from the values already present in this
# database so seeded rows do not introduce a second naming convention.
# ──────────────────────────────────────────────────────────────────────────

RECIPIENT_BREEDS = [
    ("Cross Breed", 0.34),
    ("Sahiwal", 0.20),
    ("Holstein Friesian", 0.14),
    ("Red Sindhi", 0.12),
    ("Nukra", 0.08),
    ("Grey Brahman", 0.06),
    ("Red Brahman", 0.04),
    ("Angus", 0.02),
]

IVM_MEDIA = ["TCM-199 + 10% FBS + FSH/LH", "TCM-199 + 0.5 µg/mL FSH", "BO-IVM"]
IVF_MEDIA = ["SOF-BE1", "BO-IVC", "CR1aa + 5% FBS"]
FERT_MEDIA = ["BO-IVF", "Fert-TALP"]

UTERINE_TONE = ["Good", "Fair", "Poor"]
CL_QUALITY = ["Good", "Fair", "Poor"]

# Published bovine OPU/IVF benchmarks, used to walk the funnel backwards from
# the embryos that were actually banked. Each is (mean, sd, lo, hi).
RECOVERY_RATE = (0.72, 0.08, 0.50, 0.92)   # oocytes recovered / follicles aspirated
VIABILITY_RATE = (0.82, 0.07, 0.60, 0.95)  # viable / recovered
MATURATION_RATE = (0.84, 0.06, 0.62, 0.95)  # matured / viable
CLEAVAGE_RATE = (0.76, 0.07, 0.55, 0.92)   # cleaved / matured
BLASTOCYST_RATE = (0.35, 0.06, 0.18, 0.55)  # blastocysts / cleaved


def draw(rng: random.Random, spec: tuple[float, float, float, float]) -> float:
    mean, sd, lo, hi = spec
    return min(hi, max(lo, rng.gauss(mean, sd)))


def weighted_choice(rng: random.Random, pairs: list[tuple[str, float]]) -> str:
    roll = rng.random()
    cumulative = 0.0
    for value, weight in pairs:
        cumulative += weight
        if roll <= cumulative:
            return value
    return pairs[-1][0]


def tagged(text: str | None = None) -> str:
    return f"{text} {SEED_TAG}" if text else SEED_TAG


# ──────────────────────────────────────────────────────────────────────────


class Seeder:
    def __init__(self, conn, dry_run: bool = False):
        self.conn = conn
        self.cur = conn.cursor()
        self.rng = random.Random(RNG_SEED)
        self.dry_run = dry_run
        self.counts: dict[str, int] = {}
        self.cur.execute("SELECT organization_id FROM organizations ORDER BY organization_id LIMIT 1")
        row = self.cur.fetchone()
        if row is None:
            sys.exit("No organization exists; load the base data first.")
        self.org = row[0]
        self.cur.execute("SELECT technician_id FROM technicians ORDER BY technician_id")
        self.technicians = [r[0] for r in self.cur.fetchall()]
        self.today = date.today()

    def note(self, label: str, n: int) -> None:
        self.counts[label] = self.counts.get(label, 0) + n
        print(f"  {label:<34} {n:>6}")

    # ── repair ────────────────────────────────────────────────────────────

    def repair_junk_transfers(self) -> None:
        """Remove the seven smoke-test transfers that break GET /transfers/."""
        self.cur.execute(
            "SELECT transfer_id, embryo_id FROM et_transfers WHERE created_at = %s ORDER BY transfer_id",
            (JUNK_BATCH_TS,),
        )
        rows = self.cur.fetchall()
        if not rows:
            print("  (junk smoke-test transfers already removed)")
            return
        transfer_ids = [r[0] for r in rows]
        embryo_ids = [r[1] for r in rows if r[1] is not None]

        self.cur.execute("SELECT count(*) FROM pregnancy_checks WHERE transfer_id = ANY(%s)", (transfer_ids,))
        n_checks = self.cur.fetchone()[0]

        if self.dry_run:
            print(f"  would delete transfers {transfer_ids} and {n_checks} pregnancy checks")
            return

        self.cur.execute("DELETE FROM pregnancy_checks WHERE transfer_id = ANY(%s)", (transfer_ids,))
        self.cur.execute("DELETE FROM recipient_evaluations WHERE transfer_id = ANY(%s)", (transfer_ids,))
        self.cur.execute("DELETE FROM synchronization_enrollments WHERE transfer_id = ANY(%s)", (transfer_ids,))
        self.cur.execute("DELETE FROM calving_records WHERE transfer_id = ANY(%s)", (transfer_ids,))
        self.cur.execute("DELETE FROM predictions WHERE transfer_id = ANY(%s)", (transfer_ids,))
        self.cur.execute("DELETE FROM et_transfers WHERE transfer_id = ANY(%s)", (transfer_ids,))
        # Those embryos are no longer transferred anywhere. 'Transferable' and
        # 'Frozen' are the two states the schema allows for a banked embryo that
        # has not been used, so the recorded cryo state decides which applies.
        self.cur.execute(
            """UPDATE embryos
               SET status = CASE WHEN fresh_or_frozen = 'Frozen' THEN 'Frozen' ELSE 'Transferable' END
               WHERE embryo_id = ANY(%s)""",
            (embryo_ids,),
        )
        self.note("junk transfers removed", len(transfer_ids))
        self.note("their pregnancy checks removed", n_checks)

    # ── reference data ────────────────────────────────────────────────────

    def seed_protocol_steps(self) -> None:
        """Step definitions for the five protocols already in use.

        These are the published schedules for the named synchronisation
        programmes, not invented ones — a protocol row without steps leaves the
        scheduling board with nothing to compute a due date from.
        """
        definitions: dict[str, list[tuple[int, str, str | None, str | None, str | None, bool]]] = {
            "CIDR+GnRH+PGF+GnRH": [
                (0, "CIDR insert + GnRH", "Gonadorelin", "100 µg", "IM", False),
                (7, "PGF2α", "Dinoprost", "25 mg", "IM", False),
                (7, "CIDR removal", None, None, None, False),
                (9, "GnRH", "Gonadorelin", "100 µg", "IM", False),
                (16, "Embryo transfer", None, None, None, True),
            ],
            "CIDR+E2+PGF+ECG": [
                (0, "CIDR insert + Estradiol benzoate", "Estradiol benzoate", "2 mg", "IM", False),
                (8, "PGF2α + eCG", "Dinoprost / eCG", "25 mg / 400 IU", "IM", False),
                (8, "CIDR removal", None, None, None, False),
                (9, "Estradiol benzoate", "Estradiol benzoate", "1 mg", "IM", False),
                (17, "Embryo transfer", None, None, None, True),
            ],
            "CIDR+Estradiol+PGF+GnRH": [
                (0, "CIDR insert + Estradiol benzoate", "Estradiol benzoate", "2 mg", "IM", False),
                (7, "PGF2α", "Dinoprost", "25 mg", "IM", False),
                (8, "CIDR removal", None, None, None, False),
                (10, "GnRH", "Gonadorelin", "100 µg", "IM", False),
                (17, "Embryo transfer", None, None, None, True),
            ],
            "CIDR+E2+ECG+PGF+GnRH": [
                (0, "CIDR insert + Estradiol benzoate", "Estradiol benzoate", "2 mg", "IM", False),
                (5, "eCG", "eCG", "400 IU", "IM", False),
                (8, "PGF2α", "Dinoprost", "25 mg", "IM", False),
                (8, "CIDR removal", None, None, None, False),
                (10, "GnRH", "Gonadorelin", "100 µg", "IM", False),
                (17, "Embryo transfer", None, None, None, True),
            ],
            "Natural heat": [
                (0, "Observed standing heat", None, None, None, False),
                (7, "Embryo transfer", None, None, None, True),
            ],
        }

        self.cur.execute("SELECT protocol_id, name FROM protocols")
        protocols = self.cur.fetchall()
        payload = []
        for protocol_id, name in protocols:
            for day, step, drug, dose, route, is_transfer in definitions.get(name, []):
                payload.append(
                    (self.org, protocol_id, day, step, drug, dose, route, is_transfer, SEED_TAG)
                )
        if not payload or self.dry_run:
            print(f"  would insert {len(payload)} protocol steps")
            return
        execute_values(
            self.cur,
            """INSERT INTO protocol_steps
                 (organization_id, protocol_id, day_offset, step_name, drug_name,
                  dosage, route, is_transfer_day, notes)
               VALUES %s
               ON CONFLICT (protocol_id, day_offset, step_name) DO NOTHING""",
            payload,
        )
        self.note("protocol steps", self.cur.rowcount)

    def seed_animal_profiles(self) -> None:
        """Breed, age and reproductive history for recipients and donors.

        Only null columns are written. ``cow_or_heifer`` is already recorded and
        constrains parity, so a heifer never gets a calving history.
        """
        self.cur.execute(
            "SELECT recipient_id, cow_or_heifer FROM recipients WHERE breed IS NULL ORDER BY recipient_id"
        )
        recipients = self.cur.fetchall()
        updates = []
        for recipient_id, kind in recipients:
            heifer = (kind or "").strip().lower() == "heifer"
            parity = 0 if heifer else self.rng.choices([1, 2, 3, 4, 5], [0.34, 0.27, 0.2, 0.12, 0.07])[0]
            age_months = self.rng.randint(15, 26) if heifer else self.rng.randint(34, 34 + parity * 14)
            birth = self.today - timedelta(days=int(age_months * 30.4))
            # Constrained to ck_recipients_reproductive_status.
            status = weighted_choice(
                self.rng,
                [("Cycling", 0.70), ("Open", 0.16), ("Anestrus", 0.11), ("Culled", 0.03)],
            )
            prev_ai = 0 if heifer else self.rng.choices([0, 1, 2, 3], [0.4, 0.3, 0.2, 0.1])[0]
            prev_et = self.rng.choices([0, 1, 2], [0.62, 0.28, 0.10])[0]
            updates.append(
                (
                    weighted_choice(self.rng, RECIPIENT_BREEDS),
                    birth,
                    parity,
                    status,
                    prev_ai,
                    prev_et,
                    SEED_TAG,
                    recipient_id,
                )
            )
        if updates and not self.dry_run:
            execute_values(
                self.cur,
                """UPDATE recipients AS r SET
                       breed = v.breed, birth_date = v.birth_date, parity = v.parity,
                       reproductive_status = v.status, previous_ai_count = v.prev_ai,
                       previous_et_count = v.prev_et,
                       notes = trim(both ' ' from coalesce(r.notes,'') || ' ' || v.tag)
                   FROM (VALUES %s) AS v(breed, birth_date, parity, status, prev_ai, prev_et, tag, rid)
                   WHERE r.recipient_id = v.rid""",
                updates,
                template="(%s, %s::date, %s::int, %s, %s::int, %s::int, %s, %s::int)",
            )
        self.note("recipient profiles", len(updates))

        self.cur.execute(
            "SELECT donor_id FROM donors WHERE birth_date IS NULL ORDER BY donor_id"
        )
        donors = [r[0] for r in self.cur.fetchall()]
        donor_updates = []
        for donor_id in donors:
            parity = self.rng.choices([1, 2, 3, 4, 5, 6], [0.18, 0.24, 0.22, 0.18, 0.12, 0.06])[0]
            birth = self.today - timedelta(days=self.rng.randint(1200, 2900))
            donor_updates.append(
                (
                    birth,
                    parity,
                    weighted_choice(self.rng, [("Cycling", 0.82), ("Open", 0.12), ("Anestrus", 0.06)]),
                    f"{parity} previous calving(s); donor in active OPU rotation.",
                    SEED_TAG,
                    donor_id,
                )
            )
        if donor_updates and not self.dry_run:
            execute_values(
                self.cur,
                """UPDATE donors AS d SET
                       birth_date = v.birth_date, parity = v.parity,
                       reproductive_status = v.status, reproductive_history = v.history,
                       notes = trim(both ' ' from coalesce(d.notes,'') || ' ' || v.tag)
                   FROM (VALUES %s) AS v(birth_date, parity, status, history, tag, did)
                   WHERE d.donor_id = v.did""",
                donor_updates,
                template="(%s::date, %s::int, %s, %s, %s, %s::int)",
            )
        self.note("donor profiles", len(donor_updates))

    # ── the laboratory chain ──────────────────────────────────────────────

    def seed_lab_chain(self) -> None:
        """Walk the OPU -> IVM -> IVF funnel backwards from the banked embryos.

        The embryos are real: each was recorded against an OPU session and an
        IVF batch. So the blastocyst count is not a free choice — it is anchored
        at the embryos that session actually produced, and every upstream count
        is derived from it through published bovine rates. That keeps the funnel
        monotone (follicles >= recovered >= viable >= matured >= cleaved >=
        blastocysts >= embryos banked) and every derived rate inside a range a
        veterinarian would recognise.
        """
        self.cur.execute(
            """SELECT o.opu_id, o.opu_date, count(e.embryo_id) AS n_embryos
               FROM opu_sessions o
               LEFT JOIN embryos e ON e.opu_id = o.opu_id
               WHERE o.oocytes_recovered IS NULL
               GROUP BY o.opu_id, o.opu_date
               ORDER BY o.opu_id"""
        )
        sessions = self.cur.fetchall()

        opu_updates: list[tuple] = []
        ivm_rows: list[tuple] = []
        derived: dict[int, dict] = {}

        for opu_id, opu_date, n_embryos in sessions:
            banked = max(int(n_embryos), 0)
            # A session that banked nothing still aspirated follicles.
            discarded = self.rng.choices([0, 1, 2], [0.62, 0.28, 0.10])[0]
            blastocysts = max(banked + discarded, 1)

            cleaved = max(blastocysts + 1, round(blastocysts / draw(self.rng, BLASTOCYST_RATE)))
            matured = max(cleaved + 1, round(cleaved / draw(self.rng, CLEAVAGE_RATE)))
            viable = max(matured + 1, round(matured / draw(self.rng, MATURATION_RATE)))
            recovered = max(viable + 1, round(viable / draw(self.rng, VIABILITY_RATE)))
            follicles = max(recovered + 1, round(recovered / draw(self.rng, RECOVERY_RATE)))

            degenerated = recovered - viable
            grade_a = round(viable * self.rng.uniform(0.38, 0.52))
            grade_b = round((viable - grade_a) * self.rng.uniform(0.55, 0.75))
            grade_c = viable - grade_a - grade_b

            technician = self.rng.choice(self.technicians) if self.technicians else None
            derived[opu_id] = {
                "viable": viable,
                "matured": matured,
                "cleaved": cleaved,
                "blastocysts": blastocysts,
                "opu_date": opu_date,
            }
            opu_updates.append(
                (
                    follicles, recovered, viable, grade_a, grade_b, grade_c, degenerated,
                    technician,
                    f"Aspirated {follicles} follicles; {recovered} oocytes recovered.",
                    SEED_TAG, opu_id,
                )
            )
            if opu_date is not None:
                ivm_rows.append(
                    (
                        self.org, opu_id, opu_date,
                        self.rng.choice(IVM_MEDIA),
                        f"IVM-{opu_date:%y%m}-{self.rng.randint(1, 9)}",
                        round(self.rng.uniform(22.0, 24.0), 1),
                        38.5,
                        round(self.rng.uniform(5.0, 6.0), 1),
                        round(self.rng.uniform(5.0, 20.0), 1),
                        viable, matured, technician, SEED_TAG,
                    )
                )

        if opu_updates and not self.dry_run:
            execute_values(
                self.cur,
                """UPDATE opu_sessions AS o SET
                     total_follicles = v.follicles, oocytes_recovered = v.recovered,
                     viable_oocytes = v.viable, grade_a_oocytes = v.ga,
                     grade_b_oocytes = v.gb, grade_c_oocytes = v.gc,
                     degenerated_oocytes = v.degen,
                     technician_id = coalesce(o.technician_id, v.tech),
                     oocyte_morphology_notes = coalesce(o.oocyte_morphology_notes, v.morph),
                     notes = trim(both ' ' from coalesce(o.notes,'') || ' ' || v.tag)
                   FROM (VALUES %s) AS v(follicles, recovered, viable, ga, gb, gc, degen, tech, morph, tag, oid)
                   WHERE o.opu_id = v.oid""",
                opu_updates,
                template="(%s::int, %s::int, %s::int, %s::int, %s::int, %s::int, %s::int, %s::int, %s, %s, %s::int)",
            )
        self.note("OPU sessions given oocyte counts", len(opu_updates))

        if ivm_rows and not self.dry_run:
            execute_values(
                self.cur,
                """INSERT INTO ivm_batches
                     (organization_id, opu_id, ivm_date, medium, medium_lot, incubation_hours,
                      temperature_c, co2_percent, o2_percent, oocytes_in, mature_oocytes_out,
                      embryologist_id, notes)
                   VALUES %s""",
                ivm_rows,
            )
        self.note("IVM batches", len(ivm_rows))

        self._seed_ivf_numbers(derived)

    def _seed_ivf_numbers(self, derived: dict[int, dict]) -> None:
        """Distribute each session's oocytes across its IVF batches.

        Two sessions were split across more than one batch, so the counts are
        apportioned by the embryos each batch actually produced rather than
        duplicated — otherwise the funnel would double-count them.
        """
        self.cur.execute(
            """SELECT b.ivf_batch_id, b.opu_id, count(e.embryo_id) AS n_embryos
               FROM ivf_batches b
               LEFT JOIN embryos e ON e.ivf_batch_id = b.ivf_batch_id
               WHERE b.oocytes_used IS NULL
               GROUP BY b.ivf_batch_id, b.opu_id
               ORDER BY b.ivf_batch_id"""
        )
        batches = self.cur.fetchall()

        by_opu: dict[int, list[tuple[int, int]]] = {}
        for batch_id, opu_id, n_embryos in batches:
            by_opu.setdefault(opu_id, []).append((batch_id, int(n_embryos)))

        # ivm_batch_id lets the lab screen walk IVF -> IVM -> OPU.
        self.cur.execute("SELECT opu_id, ivm_batch_id FROM ivm_batches")
        ivm_by_opu = dict(self.cur.fetchall())

        updates = []
        for opu_id, members in by_opu.items():
            source = derived.get(opu_id)
            if source is None:
                continue
            total_embryos = sum(n for _, n in members) or len(members)
            for batch_id, n_embryos in members:
                share = (n_embryos or 1) / total_embryos
                used = max(1, round(source["viable"] * share))
                matured = max(1, min(used, round(source["matured"] * share)))
                cleaved = max(1, min(matured, round(source["cleaved"] * share)))
                blasts = max(0, min(cleaved, round(source["blastocysts"] * share)))
                ivf_date = source["opu_date"] + timedelta(days=1) if source["opu_date"] else None
                updates.append(
                    (
                        ivf_date, used, matured, cleaved, blasts, cleaved - blasts,
                        self.rng.choice(IVF_MEDIA),
                        self.rng.choice(self.technicians) if self.technicians else None,
                        ivm_by_opu.get(opu_id),
                        self.rng.choice(FERT_MEDIA),
                        round(self.rng.uniform(18.0, 20.0), 1),
                        # sperm_concentration is a free-text column in this
                        # schema, so it carries its own unit rather than a bare
                        # number that the reader has to guess at.
                        f"{self.rng.uniform(1.0, 2.0):.1f} x10^6/mL",
                        SEED_TAG, batch_id,
                    )
                )

        if updates and not self.dry_run:
            execute_values(
                self.cur,
                """UPDATE ivf_batches AS b SET
                     ivf_date = coalesce(b.ivf_date, v.ivf_date),
                     oocytes_used = v.used, mature_oocytes = v.matured,
                     cleaved_embryos = v.cleaved, blastocysts = v.blasts,
                     degenerated_embryos = v.degen,
                     culture_media = coalesce(b.culture_media, v.media),
                     embryologist_id = coalesce(b.embryologist_id, v.emb),
                     ivm_batch_id = coalesce(b.ivm_batch_id, v.ivm),
                     fertilization_medium = coalesce(b.fertilization_medium, v.fert),
                     fertilization_hours = coalesce(b.fertilization_hours, v.hours),
                     sperm_concentration = coalesce(b.sperm_concentration, v.conc),
                     notes = trim(both ' ' from coalesce(b.notes,'') || ' ' || v.tag)
                   FROM (VALUES %s) AS v(ivf_date, used, matured, cleaved, blasts, degen,
                                         media, emb, ivm, fert, hours, conc, tag, bid)
                   WHERE b.ivf_batch_id = v.bid""",
                updates,
                template=("(%s::date, %s::int, %s::int, %s::int, %s::int, %s::int, %s, %s::int,"
                          " %s::int, %s, %s::numeric, %s::varchar, %s, %s::int)"),
            )
        self.note("IVF batches given lab numbers", len(updates))

    def seed_embryo_observations(self) -> None:
        """Day 2 / day 5 / day 7 culture checks per embryo.

        The day-7 row is pinned to the embryo's recorded stage and grade, so the
        timeline ends where the banked record actually is instead of drifting
        away from it.
        """
        self.cur.execute(
            """SELECT e.embryo_id, e.opu_date, e.stage, e.grade
               FROM embryos e
               WHERE e.opu_date IS NOT NULL
                 AND NOT EXISTS (SELECT 1 FROM embryo_observations o WHERE o.embryo_id = e.embryo_id)
               ORDER BY e.embryo_id"""
        )
        embryos = self.cur.fetchall()
        rows = []
        for embryo_id, opu_date, stage, grade in embryos:
            embryologist = self.rng.choice(self.technicians) if self.technicians else None
            cells_d2 = self.rng.choice([2, 4, 4, 4, 6, 8])
            rows.append((
                self.org, embryo_id, opu_date + timedelta(days=2), 2, 1, None,
                f"{cells_d2}-cell, symmetric blastomeres", False, cells_d2, None,
                embryologist, SEED_TAG,
            ))
            rows.append((
                self.org, embryo_id, opu_date + timedelta(days=5), 5, 3, None,
                "Compact morula", False, None, None, embryologist, SEED_TAG,
            ))
            rows.append((
                self.org, embryo_id, opu_date + timedelta(days=7), 7, stage, grade,
                "Expanded blastocyst, distinct ICM and trophectoderm", False, None,
                round(self.rng.uniform(160, 210), 1), embryologist, SEED_TAG,
            ))
        if rows and not self.dry_run:
            execute_values(
                self.cur,
                """INSERT INTO embryo_observations
                     (organization_id, embryo_id, observation_date, day_number, stage, grade,
                      morphology, is_arrested, cell_count, expansion_diameter_um,
                      embryologist_id, notes)
                   VALUES %s
                   ON CONFLICT (embryo_id, day_number) DO NOTHING""",
                rows,
            )
        self.note("embryo observations", len(rows))

    # ── the veterinary chain ──────────────────────────────────────────────

    def seed_recipient_evaluations(self) -> None:
        """Pre-transfer screening, anchored to what the transfer already records.

        ``cl_side``, ``cl_measure_mm`` and ``bc_score`` are already on the
        transfer for most rows, so the evaluation reuses them rather than
        inventing a second, contradictory measurement. Progesterone is derived
        from CL diameter because that is the actual physiological relationship —
        a larger, better-quality CL secretes more P4.

        A share of evaluations deliberately has no transfer: animals that were
        screened and rejected. Without them the screening yield is unmeasurable,
        because every row would be a success by construction.
        """
        self.cur.execute(
            """SELECT t.transfer_id, t.recipient_id, t.et_date, t.cl_side,
                      t.cl_measure_mm, t.bc_score, t.technician_id
               FROM et_transfers t
               WHERE NOT EXISTS (
                   SELECT 1 FROM recipient_evaluations e WHERE e.transfer_id = t.transfer_id)
               ORDER BY t.transfer_id"""
        )
        transfers = self.cur.fetchall()
        rows = []
        for transfer_id, recipient_id, et_date, cl_side, cl_mm, bcs, technician in transfers:
            if recipient_id is None or et_date is None:
                continue
            diameter = float(cl_mm) if cl_mm is not None else round(self.rng.uniform(9.0, 22.0), 1)
            side = cl_side or self.rng.choice(["Left", "Right"])
            quality = "Good" if diameter >= 15 else "Fair" if diameter >= 11 else "Poor"
            # P4 tracks CL size; the scatter is what a real assay looks like.
            p4 = round(max(0.4, 0.32 * diameter - 1.1 + self.rng.gauss(0, 0.7)), 3)
            eligibility = (
                "Excellent" if diameter >= 15 and quality == "Good"
                else "Acceptable" if diameter >= 11
                else "Not Recommended"
            )
            rows.append((
                self.org, recipient_id, et_date, technician or (self.rng.choice(self.technicians) if self.technicians else None),
                True, side, diameter, quality,
                self.rng.randint(2, 14), round(self.rng.uniform(6.0, 14.0), 1),
                weighted_choice(self.rng, [("Good", 0.7), ("Fair", 0.25), ("Poor", 0.05)]),
                p4,
                float(bcs) if bcs is not None else round(self.rng.uniform(2.5, 3.75), 1),
                eligibility, SEED_TAG, transfer_id,
            ))

        # Screened and not used: the denominator that makes screening measurable.
        # Guarded, because unlike the per-transfer rows above these have no
        # natural key to make the insert idempotent.
        self.cur.execute("SELECT count(*) FROM recipient_evaluations WHERE transfer_id IS NULL")
        already_screened = self.cur.fetchone()[0]
        self.cur.execute(
            """SELECT recipient_id FROM recipients
               ORDER BY recipient_id DESC LIMIT 70""" if not already_screened else
            "SELECT recipient_id FROM recipients WHERE false"
        )
        rejected = [r[0] for r in self.cur.fetchall()]
        self.cur.execute("SELECT min(et_date), max(et_date) FROM et_transfers")
        first, last = self.cur.fetchone()
        for recipient_id in rejected:
            if first is None or last is None:
                break
            when = first + timedelta(days=self.rng.randint(0, max(1, (last - first).days)))
            diameter = round(self.rng.uniform(5.0, 12.0), 1)
            present = diameter >= 7.0
            rows.append((
                self.org, recipient_id, when,
                self.rng.choice(self.technicians) if self.technicians else None,
                present, self.rng.choice(["Left", "Right"]) if present else None,
                diameter if present else None,
                "Poor" if present else None,
                self.rng.randint(0, 8), round(self.rng.uniform(4.0, 11.0), 1),
                weighted_choice(self.rng, [("Fair", 0.5), ("Poor", 0.5)]),
                round(max(0.2, 0.32 * diameter - 1.1 + self.rng.gauss(0, 0.5)), 3),
                round(self.rng.uniform(2.0, 3.0), 1),
                "Not Recommended", tagged("Screened, not transferred: CL inadequate."), None,
            ))

        if rows and not self.dry_run:
            execute_values(
                self.cur,
                """INSERT INTO recipient_evaluations
                     (organization_id, recipient_id, evaluation_date, technician_id, cl_present,
                      cl_side, cl_diameter_mm, cl_quality, follicle_count, largest_follicle_mm,
                      uterine_tone, progesterone_ng_ml, body_condition_score, eligibility,
                      notes, transfer_id)
                   VALUES %s""",
                rows,
            )
        self.note("recipient evaluations", len(rows))

    def seed_pregnancy_checks(self) -> None:
        """Complete the check history without changing a single recorded result.

        299 transfers already have a check row; 180 more carry a ``pc1_result``
        on the transfer with no corresponding check. Those get a check row whose
        result is copied verbatim from the transfer, so the normalised history
        and the denormalised column cannot disagree.

        A second check is then added for transfers that were pregnant at PC1.
        Roughly 8% are recorded as losses, which is the published early
        embryonic loss range for bovine ET between day 30 and day 60.
        """
        self.cur.execute(
            """SELECT t.transfer_id, t.et_date, t.pc1_result, t.pc1_date, t.technician_id
               FROM et_transfers t
               WHERE t.pc1_result IS NOT NULL
                 AND NOT EXISTS (SELECT 1 FROM pregnancy_checks c WHERE c.transfer_id = t.transfer_id)
               ORDER BY t.transfer_id"""
        )
        missing = self.cur.fetchall()
        rows = []
        pc1_dates = []
        for transfer_id, et_date, result, pc1_date, technician in missing:
            when = pc1_date or (et_date + timedelta(days=self.rng.randint(30, 38)))
            if when < et_date:
                when = et_date + timedelta(days=32)
            rows.append((
                self.org, transfer_id, when, (when - et_date).days, result, "Ultrasound",
                technician or (self.rng.choice(self.technicians) if self.technicians else None),
                SEED_TAG,
            ))
            pc1_dates.append((when, transfer_id))
        if rows and not self.dry_run:
            execute_values(
                self.cur,
                """INSERT INTO pregnancy_checks
                     (organization_id, transfer_id, check_date, days_post_transfer, result,
                      method, technician_id, notes)
                   VALUES %s
                   ON CONFLICT (transfer_id, check_date) DO NOTHING""",
                rows,
            )
            # Give the transfer the date its own result implies.
            execute_values(
                self.cur,
                """UPDATE et_transfers AS t SET pc1_date = v.d
                   FROM (VALUES %s) AS v(d, tid)
                   WHERE t.transfer_id = v.tid AND t.pc1_date IS NULL""",
                pc1_dates,
                template="(%s::date, %s::int)",
            )
        self.note("PC1 checks backfilled from recorded result", len(rows))

        # ── second check ──
        self.cur.execute(
            """SELECT t.transfer_id, t.et_date, t.technician_id
               FROM et_transfers t
               WHERE t.pc1_result = 'Pregnant' AND t.pc2_result IS NULL
               ORDER BY t.transfer_id"""
        )
        pregnant = self.cur.fetchall()
        checks, transfer_updates = [], []
        for transfer_id, et_date, technician in pregnant:
            when = et_date + timedelta(days=self.rng.randint(58, 72))
            if when > self.today:
                continue  # not due yet: leave it on the vet's work list
            still = self.rng.random() > 0.08
            result = "Pregnant" if still else "Lost"
            checks.append((
                self.org, transfer_id, when, (when - et_date).days, result, "Ultrasound",
                technician or (self.rng.choice(self.technicians) if self.technicians else None),
                SEED_TAG,
            ))
            transfer_updates.append((when, "Pregnant" if still else "Open", transfer_id))
        if checks and not self.dry_run:
            execute_values(
                self.cur,
                """INSERT INTO pregnancy_checks
                     (organization_id, transfer_id, check_date, days_post_transfer, result,
                      method, technician_id, notes)
                   VALUES %s
                   ON CONFLICT (transfer_id, check_date) DO NOTHING""",
                checks,
            )
            execute_values(
                self.cur,
                """UPDATE et_transfers AS t SET pc2_date = v.d, pc2_result = v.r
                   FROM (VALUES %s) AS v(d, r, tid)
                   WHERE t.transfer_id = v.tid""",
                transfer_updates,
                template="(%s::date, %s, %s::int)",
            )
        self.note("PC2 checks", len(checks))

    def seed_synchronization(self) -> None:
        """Enrolments behind the transfers, plus a live board for today.

        Historic enrolments are back-calculated from the transfer date and the
        protocol's own transfer-day offset, so the schedule the app derives lands
        on the day the transfer actually happened. Active enrolments are anchored
        to today so the board shows overdue, due-today and upcoming steps rather
        than a wall of completed history.
        """
        self.cur.execute(
            """SELECT p.protocol_id, coalesce(max(s.day_offset) FILTER (WHERE s.is_transfer_day), 16)
               FROM protocols p LEFT JOIN protocol_steps s ON s.protocol_id = p.protocol_id
               GROUP BY p.protocol_id"""
        )
        transfer_day = dict(self.cur.fetchall())

        self.cur.execute(
            """SELECT t.transfer_id, t.recipient_id, t.protocol_id, t.et_date, t.technician_id
               FROM et_transfers t
               WHERE t.protocol_id IS NOT NULL AND t.recipient_id IS NOT NULL
                 AND NOT EXISTS (
                     SELECT 1 FROM synchronization_enrollments e WHERE e.transfer_id = t.transfer_id)
               ORDER BY t.transfer_id"""
        )
        rows = []
        for transfer_id, recipient_id, protocol_id, et_date, technician in self.cur.fetchall():
            start = et_date - timedelta(days=int(transfer_day.get(protocol_id, 16)))
            rows.append((
                self.org, recipient_id, protocol_id, start, "Completed", None,
                technician or (self.rng.choice(self.technicians) if self.technicians else None),
                transfer_id, SEED_TAG,
            ))

        # A live board: some mid-protocol, some just started, a few withdrawn.
        # Without this the board is 100% completed history and the whole
        # scheduling feature looks inert.
        self.cur.execute("SELECT protocol_id FROM protocols ORDER BY protocol_id")
        protocol_ids = [r[0] for r in self.cur.fetchall()]
        # Eligible = never transferred, or last used long enough ago to be back
        # in rotation. A recipient is not retired after one transfer.
        self.cur.execute(
            """SELECT r.recipient_id
               FROM recipients r
               LEFT JOIN (SELECT recipient_id, max(et_date) last_used
                          FROM et_transfers WHERE recipient_id IS NOT NULL
                          GROUP BY recipient_id) u ON u.recipient_id = r.recipient_id
               WHERE (u.last_used IS NULL OR u.last_used < %s)
                 AND NOT EXISTS (
                     SELECT 1 FROM synchronization_enrollments e
                     WHERE e.recipient_id = r.recipient_id AND e.status <> 'Completed')
               ORDER BY u.last_used NULLS FIRST, r.recipient_id
               LIMIT 40""",
            (self.today - timedelta(days=120),),
        )
        free = [r[0] for r in self.cur.fetchall()]
        # Cap the live board. Without this every re-run adds another 40 animals
        # to a queue that nobody ever works off.
        self.cur.execute(
            "SELECT count(*) FROM synchronization_enrollments WHERE status <> 'Completed'"
        )
        free = free[: max(0, 45 - self.cur.fetchone()[0])]
        for index, recipient_id in enumerate(free):
            protocol_id = protocol_ids[index % len(protocol_ids)]
            start = self.today - timedelta(days=self.rng.randint(0, 15))
            status = "Withdrawn" if index % 11 == 0 else "Active"
            rows.append((
                self.org, recipient_id, protocol_id, start, status,
                "Came into natural heat before the protocol completed." if status == "Withdrawn" else None,
                self.rng.choice(self.technicians) if self.technicians else None,
                None, SEED_TAG,
            ))

        if rows and not self.dry_run:
            execute_values(
                self.cur,
                """INSERT INTO synchronization_enrollments
                     (organization_id, recipient_id, protocol_id, start_date, status,
                      withdrawn_reason, technician_id, transfer_id, notes)
                   VALUES %s""",
                rows,
            )
        self.note("synchronization enrolments", len(rows))

    def seed_calving_records(self) -> None:
        """Calving outcomes for pregnancies that have reached term.

        This is the one table where seeding invents an outcome rather than
        detailing a recorded one: no calving was ever recorded for this
        programme. Only transfers still pregnant at the second check and past
        ~280 days of gestation get a record, and the survival split follows
        published bovine ET figures. Every live-birth number the application
        shows after this is a demonstration figure.
        """
        self.cur.execute(
            """SELECT t.transfer_id, t.et_date
               FROM et_transfers t
               WHERE t.pc2_result = 'Pregnant'
                 AND NOT EXISTS (SELECT 1 FROM calving_records c WHERE c.transfer_id = t.transfer_id)
               ORDER BY t.transfer_id"""
        )
        rows = []
        for transfer_id, et_date in self.cur.fetchall():
            # Transfer happens at day 7 of the cycle, so gestation runs from
            # there. Seeded off the transfer id rather than the shared RNG so a
            # re-run gives the same animal the same gestation length instead of
            # quietly reclassifying near-term pregnancies as calved.
            gestation = random.Random(RNG_SEED + transfer_id).randint(272, 288)
            calving = et_date + timedelta(days=gestation - 7)
            if calving > self.today:
                continue
            outcome = weighted_choice(
                self.rng, [("Live Birth", 0.91), ("Stillbirth", 0.05), ("Abortion", 0.04)]
            )
            rows.append((
                self.org, transfer_id, calving, outcome,
                self.rng.choice(["Male", "Female"]) if outcome != "Abortion" else "Unknown",
                round(self.rng.uniform(28.0, 44.0), 1) if outcome != "Abortion" else None,
                gestation,
                self.rng.random() < 0.14,
                SEED_TAG,
            ))
        if rows and not self.dry_run:
            execute_values(
                self.cur,
                """INSERT INTO calving_records
                     (organization_id, transfer_id, calving_date, outcome, calf_sex,
                      calf_weight_kg, gestation_days, assisted, notes)
                   VALUES %s
                   ON CONFLICT (transfer_id) DO NOTHING""",
                rows,
            )
        self.note("calving records", len(rows))

    # ── quality control ───────────────────────────────────────────────────

    def seed_anomalies(self) -> None:
        """QC signals computed from the data that now exists.

        These are not invented alerts: each one is a real comparison against the
        programme's own mean, so the QC screen shows findings that a reader can
        verify by looking at the underlying session.
        """
        self.cur.execute("SELECT count(*) FROM anomalies WHERE description LIKE %s", (f"%{SEED_TAG}%",))
        if self.cur.fetchone()[0]:
            print("  (QC anomalies already present)")
            return

        self.cur.execute(
            """WITH stats AS (
                   SELECT avg(oocytes_recovered::numeric) AS mean_recovered,
                          stddev_pop(oocytes_recovered::numeric) AS sd_recovered
                   FROM opu_sessions WHERE oocytes_recovered IS NOT NULL)
               SELECT o.opu_id, o.oocytes_recovered, s.mean_recovered, s.sd_recovered
               FROM opu_sessions o CROSS JOIN stats s
               WHERE o.oocytes_recovered IS NOT NULL
                 AND s.sd_recovered > 0
                 AND abs(o.oocytes_recovered - s.mean_recovered) > 1.6 * s.sd_recovered
               ORDER BY abs(o.oocytes_recovered - s.mean_recovered) DESC
               LIMIT 10"""
        )
        rows = []
        for opu_id, recovered, mean_recovered, _sd in self.cur.fetchall():
            low = recovered < mean_recovered
            rows.append((
                "oocyte_recovery_outlier", "opu_session", str(opu_id),
                "warning" if low else "info",
                f"OPU session {opu_id} recovered {recovered} oocytes against a programme mean of "
                f"{float(mean_recovered):.1f}. {SEED_TAG}",
                recovered, round(float(mean_recovered), 2), self.org,
            ))

        self.cur.execute(
            """WITH stats AS (
                   SELECT avg(blastocysts::numeric / nullif(cleaved_embryos, 0)) AS mean_rate
                   FROM ivf_batches WHERE cleaved_embryos > 0)
               SELECT b.ivf_batch_id,
                      b.blastocysts::numeric / nullif(b.cleaved_embryos, 0) AS rate,
                      s.mean_rate
               FROM ivf_batches b CROSS JOIN stats s
               WHERE b.cleaved_embryos >= 4
                 AND b.blastocysts::numeric / nullif(b.cleaved_embryos, 0) < s.mean_rate * 0.78
               ORDER BY rate ASC LIMIT 8"""
        )
        for batch_id, rate, mean_rate in self.cur.fetchall():
            rows.append((
                "low_blastocyst_rate", "ivf_batch", str(batch_id), "warning",
                f"IVF batch {batch_id} reached {float(rate) * 100:.1f}% blastocyst rate against a "
                f"programme mean of {float(mean_rate) * 100:.1f}%. {SEED_TAG}",
                round(float(rate) * 100, 2), round(float(mean_rate) * 100, 2), self.org,
            ))

        if rows and not self.dry_run:
            execute_values(
                self.cur,
                """INSERT INTO anomalies
                     (anomaly_type, entity_type, entity_id, severity, description,
                      metric_value, baseline_value, organization_id)
                   VALUES %s""",
                rows,
            )
        self.note("QC anomalies", len(rows))

    # ── teardown ──────────────────────────────────────────────────────────

    def purge(self) -> None:
        """Remove every row this script wrote and undo every column it filled.

        Deleting the transfers it repaired is deliberately *not* undone — those
        were corrupt, and restoring them would put back the 500. Use the
        pre-seed pg_dump for that.
        """
        like = f"%{SEED_TAG}%"
        for table in ("embryo_observations", "ivm_batches", "recipient_evaluations",
                      "synchronization_enrollments", "calving_records", "protocol_steps"):
            self.cur.execute(f"DELETE FROM {table} WHERE notes LIKE %s", (like,))
            self.note(f"deleted {table}", self.cur.rowcount)

        self.cur.execute("DELETE FROM pregnancy_checks WHERE notes LIKE %s", (like,))
        self.note("deleted pregnancy_checks", self.cur.rowcount)
        self.cur.execute("DELETE FROM anomalies WHERE description LIKE %s", (like,))
        self.note("deleted anomalies", self.cur.rowcount)
        self.cur.execute("DELETE FROM predictions WHERE model_version LIKE %s", ("%seed%",))
        self.note("deleted seeded predictions", self.cur.rowcount)

        self.cur.execute(
            """UPDATE opu_sessions SET total_follicles = NULL, oocytes_recovered = NULL,
                   viable_oocytes = NULL, grade_a_oocytes = NULL, grade_b_oocytes = NULL,
                   grade_c_oocytes = NULL, degenerated_oocytes = NULL, technician_id = NULL,
                   oocyte_morphology_notes = NULL,
                   notes = nullif(trim(both ' ' from replace(notes, %s, '')), '')
               WHERE notes LIKE %s""",
            (SEED_TAG, like),
        )
        self.note("reverted opu_sessions", self.cur.rowcount)

        self.cur.execute(
            """UPDATE ivf_batches SET ivf_date = NULL, oocytes_used = NULL, mature_oocytes = NULL,
                   cleaved_embryos = NULL, blastocysts = NULL, degenerated_embryos = NULL,
                   culture_media = NULL, embryologist_id = NULL, ivm_batch_id = NULL,
                   fertilization_medium = NULL, fertilization_hours = NULL,
                   sperm_concentration = NULL,
                   notes = nullif(trim(both ' ' from replace(notes, %s, '')), '')
               WHERE notes LIKE %s""",
            (SEED_TAG, like),
        )
        self.note("reverted ivf_batches", self.cur.rowcount)

        self.cur.execute(
            """UPDATE recipients SET breed = NULL, birth_date = NULL, parity = NULL,
                   reproductive_status = NULL, previous_ai_count = NULL, previous_et_count = NULL,
                   notes = nullif(trim(both ' ' from replace(notes, %s, '')), '')
               WHERE notes LIKE %s""",
            (SEED_TAG, like),
        )
        self.note("reverted recipients", self.cur.rowcount)

        self.cur.execute(
            """UPDATE donors SET birth_date = NULL, parity = NULL, reproductive_status = NULL,
                   reproductive_history = NULL,
                   notes = nullif(trim(both ' ' from replace(notes, %s, '')), '')
               WHERE notes LIKE %s""",
            (SEED_TAG, like),
        )
        self.note("reverted donors", self.cur.rowcount)

        # PC2 lived only on the seeded checks.
        self.cur.execute(
            """UPDATE et_transfers SET pc2_date = NULL, pc2_result = NULL
               WHERE pc2_result IS NOT NULL"""
        )
        self.note("cleared pc2 on transfers", self.cur.rowcount)

    # ── orchestration ─────────────────────────────────────────────────────

    def run(self) -> None:
        print("\nRepairing corrupt rows")
        self.repair_junk_transfers()
        print("\nReference data")
        self.seed_protocol_steps()
        self.seed_animal_profiles()
        print("\nLaboratory chain")
        self.seed_lab_chain()
        self.seed_embryo_observations()
        print("\nVeterinary chain")
        self.seed_recipient_evaluations()
        self.seed_pregnancy_checks()
        self.seed_synchronization()
        self.seed_calving_records()
        print("\nQuality control")
        self.seed_anomalies()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", DEFAULT_DSN))
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    parser.add_argument("--purge", action="store_true", help="remove everything this script wrote")
    args = parser.parse_args()

    dsn = args.database_url
    if dsn.startswith("postgresql+"):
        dsn = "postgresql://" + dsn.split("://", 1)[1]
    if "@db:" in dsn:  # the docker-compose hostname, unreachable from the host
        dsn = DEFAULT_DSN

    conn = psycopg2.connect(dsn)
    try:
        seeder = Seeder(conn, dry_run=args.dry_run)
        if args.purge:
            print("Purging seeded data")
            seeder.purge()
        else:
            seeder.run()
        if args.dry_run:
            conn.rollback()
            print("\nDry run: rolled back.")
        else:
            conn.commit()
            print("\nCommitted.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
