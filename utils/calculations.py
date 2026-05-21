import re

from models import Threshold


AIR_MATRICES = ("Area Air", "Personal Air")

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
    if sample.matrix in AIR_MATRICES:
        comparison_value = compute_twa_8hr(sample, result)
        basis = "8-hr TWA"
        units = result.result_units
    elif result.result_numeric is not None:
        comparison_value = result.result_numeric
        basis = "Direct"
        units = result.result_units
    else:
        comparison_value = None
        basis = None
        units = None

    thresholds = (
        Threshold.query
        .filter_by(analyte=result.analyte, matrix=sample.matrix, active=True)
        .all()
    )

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
        evaluations.append({
            "threshold": t,
            "exceeded": exceeded,
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

    if pel_exceeded:
        overall_status = "exceeded"
    elif action_exceeded:
        overall_status = "warning"
    else:
        overall_status = "ok"

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
