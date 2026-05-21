import csv
import io
import re
from functools import wraps

from flask import Response, abort
from flask_login import current_user, login_required

from utils.calculations import evaluate_result


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


CSV_HEADERS = [
    "Project Number",
    "Project Name",
    "Project Status",
    "Client Sample ID",
    "Lab Sample ID",
    "Lab WorkOrder",
    "Matrix",
    "Collection Date",
    "Collection Time",
    "Sample Volume",
    "Pump Flow Rate",
    "Employee Name",
    "Work Area",
    "Task Description",
    "Analyte",
    "Result",
    "Result Numeric",
    "Units",
    "RL",
    "DF",
    "Method",
    "Date Analyzed",
    "Comparison Basis",
    "Comparison Value",
    "Flag Status",
    "Thresholds Exceeded",
    "Thresholds Approaching",
]

FLAG_DISPLAY = {
    "exceeded": "Exceeded",
    "warning": "Warning",
    "ok": "OK",
    "no_thresholds": "No Data",
    "no_value": "No Data",
    "no_results": "No Data",
}


def _format_value(v):
    if v is None:
        return ""
    return str(v)


def _format_date(d):
    if d is None:
        return ""
    return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)


def _format_datetime(d):
    if d is None:
        return ""
    return d.strftime("%Y-%m-%d %H:%M") if hasattr(d, "strftime") else str(d)


def _threshold_labels(evaluations, key):
    return [
        f"{e['threshold'].threshold_name} ({e['threshold'].regulatory_body})"
        for e in evaluations
        if e.get(key)
    ]


def build_csv_rows(samples):
    """Yield the CSV header row followed by one row per analyte result.

    Samples without results produce no rows. Sample-level fields repeat per
    result so the file is flat and pivot-friendly.
    """
    yield CSV_HEADERS
    for sample in samples:
        project = sample.project
        project_number = project.project_number if project else ""
        project_name = project.name if project else ""
        project_status = project.status if project else ""
        for result in sample.results:
            ev = evaluate_result(sample, result)
            exceeded_names = _threshold_labels(ev["evaluations"], "exceeded")
            approaching_names = _threshold_labels(ev["evaluations"], "approaching")
            yield [
                project_number,
                project_name,
                project_status,
                sample.client_sample_id or "",
                sample.lab_sample_id or "",
                sample.lab_workorder or "",
                sample.matrix or "",
                _format_date(sample.collection_date),
                sample.collection_time or "",
                sample.sample_volume or "",
                sample.pump_flow_rate or "",
                sample.employee_name or "",
                sample.work_area or "",
                sample.task_description or "",
                result.analyte or "",
                result.result_value or "",
                _format_value(result.result_numeric),
                result.result_units or "",
                result.reporting_limit or "",
                result.dilution_factor or "",
                result.method_reference or "",
                _format_datetime(result.date_analyzed),
                ev.get("comparison_basis") or "",
                _format_value(ev.get("comparison_value")),
                FLAG_DISPLAY.get(ev.get("overall_status"), ""),
                "; ".join(exceeded_names),
                "; ".join(approaching_names),
            ]


def csv_response(samples, filename):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerows(build_csv_rows(samples))
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def safe_filename_part(value):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value or "unknown")
