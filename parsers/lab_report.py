import base64
import json
import os
import re
from typing import Optional

import anthropic


PROJECT_NUMBER_RE = re.compile(r"(\d{1,3}-\d{4})")


# Sample-ID prefix codes used by CCC's naming conventions. Detected at the
# start, middle (between dashes), or end of a client sample ID.
#
# Test cases the regex needs to handle:
#   - prefix at start:  "AM-001"
#   - middle:           "1633-AM-001"
#   - end:              "1633-001-AM", "1633-26-2026-PM"
PREFIX_MAP = {
    "AM": "Area Air",
    "PM": "Personal Air",
    "SS": "Soil",
    "ES": "Excavated Soil",
    "WW": "Liquid",
    "PC": "Paint Chip",
    "WS": "Wipe",
    "SA": "Spent Abrasive",
}

PREFIX_RE = re.compile(r"(?:^|-)([A-Za-z]{2})(?:-|$)")

# Relaxed boundary set: digits, dashes, underscores, whitespace. Catches
# legacy IDs where the matrix code is jammed against digits or separated by
# underscores instead of dashes, e.g.:
#   "1643-37-2026PM"            (PM bounded by digit and end-of-string)
#   "1643-37-2026PM (Pump #1)"  (PM bounded by digit and space)
#   "1604-001-2022MTLS_PM_BLANK" (PM bounded by underscores)
PREFIX_RE_RELAXED = re.compile(r"(?:^|[\d\-_\s])([A-Za-z]{2})(?:[\d\-_\s]|$)")


MATRIX_OPTIONS = [
    "Area Air",
    "Personal Air",
    "Soil",
    "Excavated Soil",
    "Liquid",
    "Spent Abrasive",
    "Paint Chip",
    "Wipe",
    "Other",
]


SYSTEM_PROMPT = (
    "You extract structured data from environmental lab analytical reports. "
    "Output ONLY valid JSON matching the provided schema. "
    "Use 'ND' for non-detect values. "
    "Use null for missing fields. "
    "Do not include commentary or markdown fences."
)


SCHEMA_DESCRIPTION = """\
{
  "lab": "Lab name as printed on the report (string)",
  "workorder": "Work order or lab job number (string) or null",
  "project_text": "Project name / number / location text from the cover page (string) or null",
  "samples": [
    {
      "client_sample_id": "Sample ID as labeled by the client (string)",
      "lab_sample_id": "Sample ID assigned by the lab (string)",
      "matrix_raw": "Matrix as printed on the report (string, e.g. 'Air', 'Soil', 'Water', 'Wipe', 'Spent Abrasive', 'Paint Chip')",
      "collection_date": "Date the sample was collected (string, format as printed) or null",
      "collection_start_time": "Start time of sampling in HH:MM (string) or null. For Air samples, prefer the value from the handwritten chain-of-custody (COC) form.",
      "collection_end_time": "End time of sampling in HH:MM (string) or null. Typically present on both the analytical report and the COC.",
      "sample_volume": "Volume / amount of sample with units (string) or null",
      "pump_flow_rate": "Air flow rate for Air samples with units (string, e.g. '2 L/min' or '2.0 L/min') or null. Look on the handwritten COC.",
      "method": "Analytical method reference (string, e.g. 'N7303m', 'SW6020') or null",
      "units": "Default units for results in this sample (string) or null",
      "results": [
        {
          "analyte": "Analyte name as printed (string, e.g. 'Pb', 'Lead')",
          "result_value": "Reported value as a string. Use 'ND' for non-detect. Use the printed number for numeric results (e.g. '12', '0.79').",
          "result_units": "Units for this result (string) or null",
          "reporting_limit": "Reporting limit / detection limit (string) or null",
          "dilution_factor": "Dilution factor (string) or null",
          "date_analyzed": "Date (and time if printed) the analysis was performed (string) or null"
        }
      ]
    }
  ]
}
"""


USER_PROMPT = (
    "Extract the structured lab report data from the attached PDF into a JSON "
    "object that matches this schema (treat the schema values as field "
    "descriptions, not literal output):\n\n"
    f"{SCHEMA_DESCRIPTION}\n\n"
    "Important guidance:\n"
    "- Read ALL pages of the PDF, including any handwritten chain-of-custody "
    "(COC) form. The COC is usually on the last page or two, often handwritten, "
    "and is the source of truth for sampling times and pump flow rate.\n"
    "- For Air samples (Area Air or Personal Air), extract from the COC: "
    "the sampling start time, the sampling end time, and the air flow rate "
    "(typically written as '2 L/min' or '2.0 L/min').\n"
    "- The lab's analytical report often shows only one timestamp (the end "
    "time). When start and end times differ between the COC and the analytical "
    "report, prefer the COC for the start time.\n"
    "- pump_flow_rate should include the units exactly as printed.\n"
    "- collection_start_time and collection_end_time should be in HH:MM format "
    "(24-hour preferred) if possible; otherwise return the printed text.\n"
    "Return ONLY the JSON object."
)


def _detect_prefix_code(client_sample_id: Optional[str]) -> Optional[str]:
    """Find the 2-letter matrix prefix code in the sample ID.

    Strict canonical pattern first (codes bounded by dashes or string edges).
    If that fails, fall back to a relaxed pattern that also accepts digit,
    underscore, and whitespace boundaries — for legacy IDs like
    "1643-37-2026PM" where the matrix code is jammed against digits. When
    the relaxed pattern yields multiple matches, prefer the rightmost.
    """
    if not client_sample_id:
        return None
    upper_id = client_sample_id.upper()

    for match in PREFIX_RE.finditer(upper_id):
        code = match.group(1)
        if code in PREFIX_MAP:
            return code

    last_valid = None
    for match in PREFIX_RE_RELAXED.finditer(upper_id):
        code = match.group(1)
        if code in PREFIX_MAP:
            last_valid = code
    return last_valid


def _detect_prefix_matrix(client_sample_id: Optional[str]) -> Optional[str]:
    """Return the matrix name for the detected prefix code, or None."""
    code = _detect_prefix_code(client_sample_id)
    return PREFIX_MAP.get(code) if code else None


def map_matrix(matrix_raw: Optional[str], client_sample_id: Optional[str]) -> str:
    raw_lower = (matrix_raw or "").strip().lower()
    prefix_matrix = _detect_prefix_matrix(client_sample_id)

    # Sample-ID prefix is the strongest signal when present.
    if prefix_matrix:
        # AM/PM only make sense if the raw matrix is air-ish (or unspecified).
        if prefix_matrix in ("Area Air", "Personal Air"):
            if "air" in raw_lower or not raw_lower:
                return prefix_matrix
        else:
            return prefix_matrix

    # Fall back to matrix_raw text inspection.
    if "air" in raw_lower:
        return "Area Air"
    if "soil" in raw_lower:
        return "Soil"
    if "water" in raw_lower or "liquid" in raw_lower:
        return "Liquid"
    if "wipe" in raw_lower:
        return "Wipe"
    if "abrasive" in raw_lower:
        return "Spent Abrasive"
    if "paint" in raw_lower and "chip" in raw_lower:
        return "Paint Chip"
    return "Other"


def parse_lab_report(file_path):
    result = {
        "lab": None,
        "workorder": None,
        "project_text": None,
        "project_number": None,
        "project_name": None,
        "samples": [],
        "errors": [],
    }

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        result["errors"].append("ANTHROPIC_API_KEY not set")
        return result

    try:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
    except Exception as exc:
        result["errors"].append(f"PDF read error: {type(exc).__name__}: {exc}")
        return result

    if not pdf_bytes:
        result["errors"].append("PDF file is empty")
        return result

    try:
        parsed = _call_claude(api_key, pdf_bytes)
    except anthropic.APIError as exc:
        result["errors"].append(f"Claude API error: {type(exc).__name__}: {exc}")
        return result
    except json.JSONDecodeError as exc:
        result["errors"].append(f"Claude response was not valid JSON: {exc}")
        return result
    except Exception as exc:
        result["errors"].append(f"Unexpected parse error: {type(exc).__name__}: {exc}")
        return result

    if not isinstance(parsed, dict):
        result["errors"].append("Claude response was not a JSON object")
        return result

    result["lab"] = parsed.get("lab")
    result["workorder"] = parsed.get("workorder")
    result["project_text"] = parsed.get("project_text")
    result["project_number"] = _extract_project_number(result["project_text"])
    result["project_name"] = _extract_project_name(result["project_text"])
    result["samples"] = _normalize_samples(parsed.get("samples") or [])
    return result


def _extract_project_number(project_text: Optional[str]) -> Optional[str]:
    if not project_text:
        return None
    match = PROJECT_NUMBER_RE.search(project_text)
    return match.group(1) if match else None


def _extract_project_name(project_text: Optional[str]) -> Optional[str]:
    if not project_text or ";" not in project_text:
        return None
    after = project_text.split(";", 1)[1].strip()
    return after or None


def _call_claude(api_key, pdf_bytes):
    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=64000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64,
                    },
                },
                {
                    "type": "text",
                    "text": USER_PROMPT,
                },
            ],
        }],
    ) as stream:
        final = stream.get_final_message()

    raw = "".join(b.text for b in final.content if b.type == "text").strip()
    return json.loads(_strip_code_fences(raw))


def _strip_code_fences(text):
    if not text.startswith("```"):
        return text
    newline_idx = text.find("\n")
    if newline_idx == -1:
        return text
    inner = text[newline_idx + 1:]
    if inner.endswith("```"):
        inner = inner[:-3]
    return inner.strip()


_BLK_TOKEN_RE = re.compile(r"(?:^|[\s\-_])BLK(?:$|[\s\-_])", re.IGNORECASE)
_FB_TB_SUFFIX_RE = re.compile(r"(?:^|[\s\-_])(FB|TB)$")


def detect_blank(client_sample_id, lab_description=None):
    """Return True if this sample appears to be a field/trip blank.

    Triggers:
      - 'blank' substring anywhere in client_sample_id (case-insensitive)
      - 'BLK' as a standalone token bounded by whitespace, dash, underscore,
        or string boundary (case-insensitive)
      - 'FB' or 'TB' as a trailing token bounded the same way, case-sensitive
        (so 'FBI', 'TBA', 'AB' don't trigger)
      - lab_description contains 'field blank' or 'trip blank' (case-insensitive)
    """
    cid = client_sample_id or ""
    cid_lower = cid.lower()

    if "blank" in cid_lower:
        return True
    if _BLK_TOKEN_RE.search(cid):
        return True
    if _FB_TB_SUFFIX_RE.search(cid):
        return True

    if lab_description:
        desc_lower = lab_description.lower()
        if "field blank" in desc_lower or "trip blank" in desc_lower:
            return True

    return False


def _normalize_samples(samples_in):
    out = []
    for sample in samples_in:
        if not isinstance(sample, dict):
            continue
        client_sample_id = sample.get("client_sample_id") or ""
        matrix_raw = sample.get("matrix_raw") or ""
        lab_description = (
            sample.get("description")
            or sample.get("notes")
            or sample.get("sample_description")
        )
        normalized = {
            "client_sample_id": client_sample_id,
            "lab_sample_id": sample.get("lab_sample_id") or "",
            "matrix_raw": matrix_raw,
            "matrix": map_matrix(matrix_raw, client_sample_id),
            "matrix_code": _detect_prefix_code(client_sample_id),
            "is_blank": detect_blank(client_sample_id, lab_description),
            "collection_date": sample.get("collection_date"),
            "collection_start_time": sample.get("collection_start_time"),
            "collection_end_time": sample.get("collection_end_time"),
            "sample_volume": sample.get("sample_volume"),
            "pump_flow_rate": sample.get("pump_flow_rate"),
            "method": sample.get("method"),
            "units": sample.get("units"),
            "results": [],
        }
        for r in sample.get("results") or []:
            if not isinstance(r, dict):
                continue
            normalized["results"].append({
                "analyte": r.get("analyte") or "",
                "result_value": r.get("result_value") or "",
                "result_units": r.get("result_units"),
                "reporting_limit": r.get("reporting_limit"),
                "dilution_factor": r.get("dilution_factor"),
                "date_analyzed": r.get("date_analyzed"),
            })
        out.append(normalized)
    return out
