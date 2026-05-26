"""CCC respirator recommendation per Personal Air TWA.

Policy: trigger respiratory protection at the Action Level (more protective
than the OSHA minimum which triggers at the PEL). APF tier selected so that
TWA / APF <= PEL.
"""

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


def recommend_respirator(twa_value, analyte, project_jurisdiction):
    """Look up AL/PEL for analyte+jurisdiction and recommend APF tier.

    Returns dict with keys: status, required_apf, respirator_type, note,
    al_value, pel_value, jurisdiction_used.
    status: "none_required" | "respirator_required" | "extreme_exposure" | "unavailable"
    """
    from models import Threshold

    jurisdiction_filter = Threshold.jurisdiction.in_([project_jurisdiction, "Both"])

    al = (
        Threshold.query
        .filter(
            Threshold.analyte == analyte,
            Threshold.threshold_type == "AL",
            jurisdiction_filter,
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
        )
        .order_by(Threshold.value.asc())
        .first()
    )

    if not al or not pel:
        return {
            "status": "unavailable",
            "note": f"No AL/PEL defined for {analyte} in {project_jurisdiction} jurisdiction",
            "required_apf": None,
            "respirator_type": None,
            "al_value": al.value if al else None,
            "pel_value": pel.value if pel else None,
            "jurisdiction_used": project_jurisdiction,
        }

    al_value = al.value
    pel_value = pel.value

    if twa_value < al_value:
        return {
            "status": "none_required",
            "note": f"TWA below Action Level ({al_value} {al.units})",
            "required_apf": None,
            "respirator_type": None,
            "al_value": al_value,
            "pel_value": pel_value,
            "jurisdiction_used": project_jurisdiction,
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
            }

    return {
        "status": "extreme_exposure",
        "required_apf": 10000,
        "respirator_type": CCC_RESPIRATOR_TIERS[-1][1],
        "note": "Exposure exceeds 10,000×PEL — IDLH conditions likely; review work practices urgently.",
        "al_value": al_value,
        "pel_value": pel_value,
        "jurisdiction_used": project_jurisdiction,
    }
