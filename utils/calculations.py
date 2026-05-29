import re
from datetime import date

from sqlalchemy import or_

from models import Threshold


AIR_MATRICES = ("Area Air", "Personal Air")

APPROACHING_THRESHOLD = 0.80

_NUMBER_RE = re.compile(r"-?\d+\.?\d*")


def _to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUMBER_RE.search(str(value).strip())
    if match is None:
        return None
    try:
        return float(match.group())
    except (TypeError, ValueError):
        return None


def _reference_date_for(sample):
    """ISO date string used to pin threshold lookups to the sample's collection date."""
    cd = getattr(sample, "collection_date", None)
    if cd is None:
        return date.today().isoformat()
    if hasattr(cd, "isoformat"):
        return cd.isoformat()
    return str(cd)


def get_applicable_thresholds(result, candidate_thresholds, basis=None):
    """Filter candidate thresholds to those whose duration matches the result basis.

    Without this filter, a 15-min STEL result would be compared against the
    8-hr TWA PEL — wrong protective framework for the sampling duration.

    The default fallback (when basis doesn't match any explicit duration rule)
    is matrix-aware: Area Air → Ambient, Personal Air → PEL/AL,
    Wipe/Soil/Paint Chip → Clearance.
    """
    basis_l = (basis or "").lower()

    def name_has(t, *needles):
        n = (t.threshold_name or "").lower()
        return any(needle in n for needle in needles)

    if any(k in basis_l for k in ("twa", "8-hr", "8 hr")):
        return [t for t in candidate_thresholds if t.threshold_type in ("PEL", "AL")]

    if any(k in basis_l for k in ("stel", "15-min", "15 min")):
        return [
            t for t in candidate_thresholds
            if t.threshold_type == "Ceiling" and name_has(t, "stel", "15")
        ]

    if any(k in basis_l for k in ("excursion", "30-min", "30 min")):
        return [
            t for t in candidate_thresholds
            if t.threshold_type == "Ceiling" and name_has(t, "excursion", "30")
        ]

    if "ceiling" in basis_l:
        return [t for t in candidate_thresholds if t.threshold_type == "Ceiling"]

    if any(k in basis_l for k in ("ambient", "naaqs", "caaqs")):
        return [t for t in candidate_thresholds if t.threshold_type == "Ambient"]

    if any(k in basis_l for k in ("clearance", "wipe", "soil")):
        return [t for t in candidate_thresholds if t.threshold_type == "Clearance"]

    # Default fallback: pick the threshold family that matches the sample matrix.
    sample_matrix = result.sample.matrix if getattr(result, "sample", None) else None
    if sample_matrix == "Area Air":
        return [t for t in candidate_thresholds if t.threshold_type == "Ambient"]
    if sample_matrix == "Personal Air":
        return [t for t in candidate_thresholds if t.threshold_type in ("PEL", "AL")]
    if sample_matrix in ("Wipe", "Soil", "Paint Chip"):
        return [t for t in candidate_thresholds if t.threshold_type == "Clearance"]
    # Truly unknown matrix — fall through to PEL/AL as the safest default.
    return [t for t in candidate_thresholds if t.threshold_type in ("PEL", "AL")]


def compute_twa_8hr(sample, result):
    if sample.matrix not in AIR_MATRICES:
        return None
    volume = _to_float(sample.sample_volume)
    flow = _to_float(sample.pump_flow_rate)
    if not volume or not flow:
        return None
    sample_minutes = volume / flow
    concentration = result.result_numeric if result.result_numeric is not None else 0.0
    twa = concentration * (sample_minutes / 480.0)
    return round(twa, 3)


def evaluate_result(sample, result):
    if sample.matrix == "Personal Air":
        comparison_value = compute_twa_8hr(sample, result)
        basis = "8-hr TWA"
        units = result.result_units
    elif sample.matrix == "Area Air":
        comparison_value = 0.0 if result.result_numeric is None else result.result_numeric
        basis = "Direct"
        units = result.result_units
    else:
        comparison_value = 0.0 if result.result_numeric is None else result.result_numeric
        basis = "Direct"
        units = result.result_units

    reference_date = _reference_date_for(sample)
    candidate_thresholds = (
        Threshold.query
        .filter(
            Threshold.analyte == result.analyte,
            Threshold.matrix == sample.matrix,
            Threshold.active.is_(True),
            or_(Threshold.effective_date.is_(None), Threshold.effective_date <= reference_date),
            or_(Threshold.superseded_date.is_(None), Threshold.superseded_date > reference_date),
        )
        .all()
    )
    thresholds = get_applicable_thresholds(result, candidate_thresholds, basis=basis)

    if not thresholds:
        return {
            "comparison_value": comparison_value,
            "comparison_basis": basis,
            "comparison_units": units,
            "evaluations": [],
            "overall_status": "no_thresholds",
        }

    if comparison_value is None:
        return {
            "comparison_value": comparison_value,
            "comparison_basis": basis,
            "comparison_units": units,
            "evaluations": [],
            "overall_status": "no_value",
        }

    evaluations = []
    for t in thresholds:
        ratio = comparison_value / t.value if t.value else 0.0
        exceeded = comparison_value >= t.value
        approaching = (
            (comparison_value >= t.value * APPROACHING_THRESHOLD)
            and not exceeded
        )
        evaluations.append({
            "threshold": t,
            "exceeded": exceeded,
            "approaching": approaching,
            "ratio": ratio,
        })

    pel_exceeded = any(
        e["exceeded"] and "Action Level" not in e["threshold"].threshold_name
        for e in evaluations
    )
    action_exceeded = any(
        e["exceeded"] and "Action Level" in e["threshold"].threshold_name
        for e in evaluations
    )
    any_approaching = any(e["approaching"] for e in evaluations)

    if pel_exceeded:
        overall_status = "exceeded"
    elif any_approaching or action_exceeded:
        overall_status = "warning"
    else:
        overall_status = "ok"

    if sample.matrix == "Wipe" and result.result_numeric is not None and result.result_numeric > 0:
        if overall_status == "ok":
            overall_status = "warning"

    return {
        "comparison_value": comparison_value,
        "comparison_basis": basis,
        "comparison_units": units,
        "evaluations": evaluations,
        "overall_status": overall_status,
    }


def worst_sample_status(sample):
    if not sample.results:
        return "no_results"

    statuses = [evaluate_result(sample, r)["overall_status"] for r in sample.results]

    if "exceeded" in statuses:
        return "exceeded"
    if "warning" in statuses:
        return "warning"
    if "ok" in statuses:
        return "ok"
    return "no_thresholds"


def project_status_summary(samples):
    summary = {"total": 0, "ok": 0, "warning": 0, "exceeded": 0, "no_data": 0}
    for s in samples:
        summary["total"] += 1
        status = worst_sample_status(s)
        if status == "exceeded":
            summary["exceeded"] += 1
        elif status == "warning":
            summary["warning"] += 1
        elif status == "ok":
            summary["ok"] += 1
        else:
            summary["no_data"] += 1
    return summary
