"""One-time backfill for samples imported before Sampling Event / AMR / FSR
flows existed.

Step 1 — group orphan Sample rows by (project_id, matrix, collection_date) and
        attach each group to a (reused or newly created) SamplingEvent.
Step 2 — create an AMR for each Personal Air / Area Air sample that lacks one.
Step 3 — create an FSR for every non-air sample that lacks one.

Idempotent: re-running skips events / AMRs / FSRs that already exist.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import (
    AirMonitorReport,
    FieldSampleRecord,
    Sample,
    SamplingEvent,
    db,
)
from utils.field_records import (
    AIR_MATRICES,
    MATRIX_CODE_MAP,
    event_date_str,
    matrix_code_for,
    parse_numeric,
)


def main():
    events_created = 0
    events_reused = 0
    amrs_created = 0
    amrs_existed = 0
    fsrs_created = 0
    fsrs_existed = 0
    samples_linked = 0
    samples_unknown_matrix = 0

    with app.app_context():
        try:
            # ============================================================
            # STEP 1: Group orphan samples into Sampling Events
            # ============================================================
            orphan_samples = (
                Sample.query
                .filter(Sample.sampling_event_id.is_(None))
                .all()
            )
            print(f"Step 1: found {len(orphan_samples)} orphan sample(s) to group.")

            groups = {}
            for s in orphan_samples:
                key = (s.project_id, s.matrix, s.collection_date)
                groups.setdefault(key, []).append(s)

            print(f"  → grouped into {len(groups)} (project, matrix, date) bucket(s).")

            group_idx = 0
            for (project_id, matrix, collection_date), samples in groups.items():
                group_idx += 1
                code = matrix_code_for(matrix)
                event_date_iso = event_date_str(collection_date)

                existing_event = (
                    SamplingEvent.query
                    .filter_by(
                        project_id=project_id,
                        matrix_code=code,
                        event_date=event_date_iso,
                    )
                    .first()
                )

                if existing_event is not None:
                    event = existing_event
                    events_reused += 1
                else:
                    event = SamplingEvent(
                        project_id=project_id,
                        matrix_code=code,
                        event_date=event_date_iso,
                        expected_sample_count=len(samples),
                        notes=(
                            f"Backfilled from {len(samples)} legacy sample(s) "
                            "imported before Sampling Event flow existed."
                        ),
                    )
                    db.session.add(event)
                    db.session.flush()
                    events_created += 1

                for s in samples:
                    s.sampling_event_id = event.id
                    if not s.matrix_code:
                        s.matrix_code = code
                    samples_linked += 1
                    if code == "UN":
                        samples_unknown_matrix += 1

                if group_idx % 10 == 0 or group_idx == len(groups):
                    print(
                        f"  ... processed {group_idx}/{len(groups)} groups "
                        f"(linked {samples_linked} samples so far)"
                    )

            # Flush so subsequent steps see the updated sampling_event_id values.
            db.session.flush()

            # ============================================================
            # STEP 2: Backfill AMR for air samples without one
            # ============================================================
            air_samples = (
                Sample.query
                .filter(Sample.matrix.in_(AIR_MATRICES))
                .all()
            )
            print(f"\nStep 2: scanning {len(air_samples)} air sample(s) for missing AMR.")

            for i, s in enumerate(air_samples, start=1):
                existing_amr = (
                    AirMonitorReport.query
                    .filter_by(client_sample_id=s.client_sample_id)
                    .first()
                )
                if existing_amr is not None:
                    amrs_existed += 1
                    if i % 10 == 0 or i == len(air_samples):
                        print(f"  ... {i}/{len(air_samples)} air samples scanned (AMRs created: {amrs_created})")
                    continue

                flow_numeric = parse_numeric(s.pump_flow_rate)
                amr = AirMonitorReport(
                    client_sample_id=s.client_sample_id,
                    project_id=s.project_id,
                    monitoring_date=event_date_str(s.collection_date),
                    time_started=s.collection_start_time,
                    time_stopped=s.collection_end_time,
                    liters_per_minute=(
                        f"{flow_numeric}" if flow_numeric is not None else None
                    ),
                    is_personal_sample=(s.matrix == "Personal Air"),
                    is_area_sample=(s.matrix == "Area Air"),
                    worker_monitored=(s.employee_name if s.matrix == "Personal Air" else None),
                    job_duties=(s.task_description if s.matrix == "Personal Air" else None),
                    monitor_location=(s.work_area if s.matrix == "Area Air" else None),
                )
                db.session.add(amr)
                amrs_created += 1

                if i % 10 == 0 or i == len(air_samples):
                    print(f"  ... {i}/{len(air_samples)} air samples scanned (AMRs created: {amrs_created})")

            # ============================================================
            # STEP 3: Backfill FSR for non-air samples without one
            # ============================================================
            non_air_samples = (
                Sample.query
                .filter(Sample.matrix.isnot(None))
                .filter(~Sample.matrix.in_(AIR_MATRICES))
                .all()
            )
            print(f"\nStep 3: scanning {len(non_air_samples)} non-air sample(s) for missing FSR.")

            for i, s in enumerate(non_air_samples, start=1):
                existing_fsr = (
                    FieldSampleRecord.query
                    .filter_by(client_sample_id=s.client_sample_id)
                    .first()
                )
                if existing_fsr is not None:
                    fsrs_existed += 1
                    if i % 10 == 0 or i == len(non_air_samples):
                        print(f"  ... {i}/{len(non_air_samples)} non-air samples scanned (FSRs created: {fsrs_created})")
                    continue

                fsr = FieldSampleRecord(
                    client_sample_id=s.client_sample_id,
                    project_id=s.project_id,
                    collection_date=event_date_str(s.collection_date),
                    collection_time=s.collection_start_time,
                    collected_by=None,
                    location_description=s.work_area,
                    matrix_specific_notes=s.task_description,
                    general_notes="Backfilled from legacy sample import.",
                )
                db.session.add(fsr)
                fsrs_created += 1

                if i % 10 == 0 or i == len(non_air_samples):
                    print(f"  ... {i}/{len(non_air_samples)} non-air samples scanned (FSRs created: {fsrs_created})")

            db.session.commit()

        except Exception as exc:
            db.session.rollback()
            print(f"\nERROR: {type(exc).__name__}: {exc}")
            raise

        print("\nBackfill complete.")
        print(
            f"Sampling Events created: {events_created} "
            f"({events_reused} existed already and were reused)."
        )
        print(
            f"AMR records created: {amrs_created} "
            f"({amrs_existed} existed already)."
        )
        print(
            f"FSR records created: {fsrs_created} "
            f"({fsrs_existed} existed already)."
        )
        print(f"Samples linked to events: {samples_linked}.")
        print(
            f"Samples with unknown matrix (matrix_code='UN'): "
            f"{samples_unknown_matrix}  [needs manual review]"
        )


if __name__ == "__main__":
    main()
