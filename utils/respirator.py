"""CCC respirator recommendation per Personal Air TWA.

Policy: trigger respiratory protection at the Action Level (more protective
than the OSHA minimum which triggers at the PEL). APF tier selected so that
TWA / APF <= PEL.
"""

from datetime import date


CCC_RESPIRATOR_TIERS = [
    (10, "Half-mask APR with HEPA filter"),
    (25, "Loose-fitting PAPR with HEPA filter"),
    (50, "Full-face APR with HEPA, full-face PAPR with HEPA, or full-face supplied-air (SAR)"),
    (1000, "SAR in pressure-demand mode or full-face PAPR with HEPA"),
    (10000, "SCBA in pressure-demand mode, or full-face SAR pressure-demand with auxiliary SCBA"),
]


JURISDICTION_LABEL = {
    "California": "California Cal-OSHA Table AC-1 + §1532.1",
    "Federal": "Federal OSHA 29 CFR 1910.1000 Table Z + 1926.62",
}


def recommend_respirator(twa_value, analyte, project_jurisdiction, collection_date=None):
    """Look up AL/PEL for analyte+jurisdiction and recommend APF tier.

    collection_date pins the threshold lookup to thresholds in effect on that
    date. Accepts an ISO date string or a date-like object; defaults to today.

    Returns dict with keys: status, required_apf, respirator_type, note,
    al_value, pel_value, jurisdiction_used.
    status: "none_required" | "respirator_required" | "extreme_exposure" | "unavailable"
    """
    from sqlalchemy import or_

    from models import Threshold

    reference_date = _reference_date(collection_date)
    jurisdiction_filter = Threshold.jurisdiction.in_([project_jurisdiction, "Both"])
    effective_filter = or_(
        Threshold.effective_date.is_(None),
        Threshold.effective_date <= reference_date,
    )
    superseded_filter = or_(
        Threshold.superseded_date.is_(None),
        Threshold.superseded_date > reference_date,
    )

    al = (
        Threshold.query
        .filter(
            Threshold.analyte == analyte,
            Threshold.threshold_type == "AL",
            jurisdiction_filter,
            effective_filter,
            superseded_filter,
        )
        .order_by(Threshold.value.asc())
        .first()
    )

    pel = (
        Threshold.query
        .filter(
            Threshold.analyte == analyte,
            Threshold.threshold_type == "PEL",
            jurisdiction_filter,
            effective_filter,
            superseded_filter,
        )
        .order_by(Threshold.value.asc())
        .first()
    )

    if not pel:
        return {
            "status": "unavailable",
            "note": f"No PEL defined for {analyte} in {project_jurisdiction} jurisdiction",
            "required_apf": None,
            "respirator_type": None,
            "al_value": al.value if al else None,
            "pel_value": None,
            "jurisdiction_used": project_jurisdiction,
            "trigger_threshold_type": None,
        }

    al_value = al.value if al else None
    pel_value = pel.value

    if al is not None:
        trigger_threshold = al_value
        trigger_threshold_type = "AL"
        below_note = f"TWA below Action Level ({al_value} {al.units})"
    else:
        trigger_threshold = pel_value / 2
        trigger_threshold_type = "Informal AL (1/2 PEL)"
        below_note = (
            f"TWA below CCC informal Action Level ({trigger_threshold} {pel.units}, "
            "calculated as 1/2 PEL since no formal AL is defined for this analyte)."
        )

    if twa_value < trigger_threshold:
        return {
            "status": "none_required",
            "note": below_note,
            "required_apf": None,
            "respirator_type": None,
            "al_value": al_value,
            "pel_value": pel_value,
            "jurisdiction_used": project_jurisdiction,
            "trigger_threshold_type": trigger_threshold_type,
        }

    for apf, description in CCC_RESPIRATOR_TIERS:
        if twa_value <= apf * pel_value:
            return {
                "status": "respirator_required",
                "required_apf": apf,
                "respirator_type": description,
                "note": None,
                "al_value": al_value,
                "pel_value": pel_value,
                "jurisdiction_used": project_jurisdiction,
                "trigger_threshold_type": trigger_threshold_type,
            }

    return {
        "status": "extreme_exposure",
        "required_apf": 10000,
        "respirator_type": CCC_RESPIRATOR_TIERS[-1][1],
        "note": "Exposure exceeds 10,000×PEL — IDLH conditions likely; review work practices urgently.",
        "al_value": al_value,
        "pel_value": pel_value,
        "jurisdiction_used": project_jurisdiction,
        "trigger_threshold_type": trigger_threshold_type,
    }


def _reference_date(value):
    if value is None:
        return date.today().isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
