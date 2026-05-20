import json
import os
import re
from typing import Optional

import anthropic
import pdfplumber


PROJECT_NUMBER_RE = re.compile(r"(\d{1,3}-\d{4})")


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
      "collection_time": "Time the sample was collected (string) or null",
      "sample_volume": "Volume / amount of sample with units (string) or null",
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


def map_matrix(matrix_raw: Optional[str], client_sample_id: Optional[str]) -> str:
    raw_lower = (matrix_raw or "").strip().lower()
    csid = (client_sample_id or "").upper()

    if "air" in raw_lower:
        if "-AM-" in csid or csid.startswith("AM-"):
            return "Area Air"
        if "-PM-" in csid or csid.startswith("PM-"):
            return "Personal Air"
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
        pdf_text = _extract_pdf_text(file_path)
    except Exception as exc:
        result["errors"].append(f"PDF extraction error: {type(exc).__name__}: {exc}")
        return result

    if not pdf_text.strip():
        result["errors"].append("PDF appears to contain no extractable text")
        return result

    try:
        parsed = _call_claude(api_key, pdf_text)
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


def _extract_pdf_text(file_path):
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _call_claude(api_key, pdf_text):
    client = anthropic.Anthropic(api_key=api_key)

    user_message = (
        "Extract the structured lab report data from the text below into a JSON object "
        "that matches this schema (treat the schema values as field descriptions, not literal output):\n\n"
        f"{SCHEMA_DESCRIPTION}\n\n"
        "Lab report text:\n"
        "---\n"
        f"{pdf_text}\n"
        "---\n\n"
        "Return ONLY the JSON object."
    )

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
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


def _normalize_samples(samples_in):
    out = []
    for sample in samples_in:
        if not isinstance(sample, dict):
            continue
        client_sample_id = sample.get("client_sample_id") or ""
        matrix_raw = sample.get("matrix_raw") or ""
        normalized = {
            "client_sample_id": client_sample_id,
            "lab_sample_id": sample.get("lab_sample_id") or "",
            "matrix_raw": matrix_raw,
            "matrix": map_matrix(matrix_raw, client_sample_id),
            "collection_date": sample.get("collection_date"),
            "collection_time": sample.get("collection_time"),
            "sample_volume": sample.get("sample_volume"),
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
