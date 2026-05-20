import re
from typing import Optional

import pdfplumber


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

LAB_SAMPLE_ID_RE = re.compile(r"\b(\d{6,8}-\d{3}[A-Z]?)\b")
DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b")


def map_matrix(matrix_raw: Optional[str], client_sample_id: Optional[str]) -> str:
    raw = (matrix_raw or "").strip()
    raw_lower = raw.lower()
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


def parse_mccampbell_pdf(file_path):
    result = {
        "lab": "McCampbell Analytical",
        "workorder": None,
        "project_text": None,
        "samples": [],
        "errors": [],
    }
    try:
        _parse_into(file_path, result)
    except Exception as exc:
        result["errors"].append(f"Parse error: {type(exc).__name__}: {exc}")
    return result


def _parse_into(file_path, result):
    page_texts = []
    page_tables = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_texts.append(page.extract_text() or "")
            try:
                page_tables.append(page.extract_tables() or [])
            except Exception:
                page_tables.append([])

    full_text = "\n".join(page_texts)

    result["workorder"] = _find_workorder(full_text)
    result["project_text"] = _find_project(full_text)

    samples_by_lab_id = {}
    _collect_samples_from_text(full_text, samples_by_lab_id, result)
    _collect_results_from_tables(page_tables, samples_by_lab_id, result)

    samples = list(samples_by_lab_id.values())
    for sample in samples:
        sample["matrix"] = map_matrix(sample.get("matrix_raw"), sample.get("client_sample_id"))
    result["samples"] = samples


def _find_workorder(text: str) -> Optional[str]:
    patterns = [
        r"Work\s*Order\s*(?:ID|#|No\.?|Number)?\s*[:\-]?\s*([A-Za-z0-9\-]+)",
        r"WorkOrder\s*[:#]?\s*([A-Za-z0-9\-]+)",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate and candidate.lower() not in {"id", "no", "number"}:
                return candidate
    return None


def _find_project(text: str) -> Optional[str]:
    match = re.search(r"^\s*Project\s*[:#]?\s*(.+?)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if match:
        candidate = match.group(1).strip()
        if candidate and candidate.lower() not in {"name", "id"}:
            return candidate
    return None


def _collect_samples_from_text(full_text: str, samples_by_lab_id: dict, result: dict) -> None:
    lines = full_text.splitlines()
    for line in lines:
        for lab_id_match in LAB_SAMPLE_ID_RE.finditer(line):
            lab_id = lab_id_match.group(1)
            if lab_id in samples_by_lab_id:
                continue
            sample = {
                "client_sample_id": "",
                "lab_sample_id": lab_id,
                "matrix_raw": "",
                "matrix": "Other",
                "collection_date": None,
                "collection_time": None,
                "sample_volume": None,
                "method": None,
                "units": None,
                "results": [],
            }
            _enrich_sample_from_line(sample, line, lab_id)
            samples_by_lab_id[lab_id] = sample


def _enrich_sample_from_line(sample: dict, line: str, lab_id: str) -> None:
    before, _, after = line.partition(lab_id)
    before_tokens = before.split()
    after_tokens = after.split()

    if before_tokens:
        sample["client_sample_id"] = before_tokens[-1]

    matrix_candidates = ["Air", "Soil", "Water", "Liquid", "Wipe", "Abrasive", "Paint", "Chip"]
    for token in after_tokens[:3]:
        if any(c.lower() in token.lower() for c in matrix_candidates):
            sample["matrix_raw"] = token
            break

    dates = DATE_RE.findall(line)
    if dates:
        sample["collection_date"] = dates[0]
    times = TIME_RE.findall(line)
    if times:
        sample["collection_time"] = times[0]


def _collect_results_from_tables(page_tables, samples_by_lab_id, result):
    if not samples_by_lab_id:
        return

    sample_for_table = None
    for tables in page_tables:
        for table in tables:
            if not table:
                continue
            header_row = _first_non_empty_row(table)
            if header_row is None:
                continue
            normalized = [_norm(c) for c in header_row]
            joined = " ".join(normalized)

            lab_id_in_table = _find_lab_id_in_table(table, samples_by_lab_id)
            if lab_id_in_table:
                sample_for_table = samples_by_lab_id[lab_id_in_table]
                _absorb_header_table(table, sample_for_table)
                continue

            if _looks_like_result_table(joined):
                target = sample_for_table or _fallback_sample(samples_by_lab_id)
                if target is None:
                    continue
                _absorb_result_table(table, target, joined)


def _first_non_empty_row(table):
    for row in table:
        if row and any(c and c.strip() for c in row if c):
            return row
    return None


def _find_lab_id_in_table(table, samples_by_lab_id) -> Optional[str]:
    for row in table:
        if not row:
            continue
        for cell in row:
            if not cell:
                continue
            for match in LAB_SAMPLE_ID_RE.finditer(str(cell)):
                if match.group(1) in samples_by_lab_id:
                    return match.group(1)
    return None


def _absorb_header_table(table, sample) -> None:
    for row in table:
        if not row:
            continue
        cells = [str(c).strip() if c else "" for c in row]
        joined = " | ".join(cells).lower()
        if "matrix" in joined and not sample.get("matrix_raw"):
            for cell in cells:
                low = cell.lower()
                if any(k in low for k in ("air", "soil", "water", "liquid", "wipe", "abrasive", "paint chip")):
                    sample["matrix_raw"] = cell
                    break
        if "method" in joined and not sample.get("method"):
            for cell in cells:
                if cell and cell.lower() != "method":
                    sample["method"] = cell
                    break
        if "volume" in joined and not sample.get("sample_volume"):
            for cell in cells:
                if cell and "volume" not in cell.lower():
                    sample["sample_volume"] = cell
                    break
        if "units" in joined and not sample.get("units"):
            for cell in cells:
                if cell and cell.lower() != "units":
                    sample["units"] = cell
                    break


def _looks_like_result_table(joined_header: str) -> bool:
    return (
        ("analyte" in joined_header or "analytes" in joined_header)
        and ("result" in joined_header)
    )


def _absorb_result_table(table, sample, joined_header) -> None:
    header_row = _first_non_empty_row(table)
    if not header_row:
        return
    index = {}
    for i, cell in enumerate(header_row):
        key = _norm(cell)
        if "analyte" in key:
            index["analyte"] = i
        elif key == "result" or key.startswith("result"):
            index.setdefault("result", i)
        elif key == "rl" or "reporting" in key:
            index["rl"] = i
        elif key == "df" or "dilution" in key:
            index["df"] = i
        elif "unit" in key:
            index["units"] = i
        elif "analyzed" in key or ("date" in key and "analyzed" in key):
            index["date_analyzed"] = i
        elif "volume" in key and "sample" not in index:
            index["volume"] = i

    if "analyte" not in index or "result" not in index:
        return

    for row in table[1:]:
        if not row:
            continue
        cells = [(str(c).strip() if c else "") for c in row]
        if not any(cells):
            continue
        analyte = _get(cells, index.get("analyte"))
        result_value = _get(cells, index.get("result"))
        if not analyte or not result_value:
            continue
        if analyte.lower().startswith("analyte"):
            continue
        sample["results"].append({
            "analyte": analyte,
            "result_value": result_value,
            "result_units": _get(cells, index.get("units")) or sample.get("units"),
            "reporting_limit": _get(cells, index.get("rl")),
            "dilution_factor": _get(cells, index.get("df")),
            "date_analyzed": _get(cells, index.get("date_analyzed")),
        })


def _fallback_sample(samples_by_lab_id):
    if not samples_by_lab_id:
        return None
    return list(samples_by_lab_id.values())[-1]


def _get(cells, idx):
    if idx is None or idx < 0 or idx >= len(cells):
        return None
    val = cells[idx]
    return val if val else None


def _norm(cell) -> str:
    if cell is None:
        return ""
    return re.sub(r"\s+", " ", str(cell)).strip().lower()
