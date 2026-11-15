"""Ham xuat file dung chung (Nguoi 3): CSV (mo duoc bang Excel, co BOM UTF-8) va Excel .xlsx."""
import csv
from datetime import date, datetime
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date, int, float, Decimal, str)):
        return value
    return str(value)


def csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
    response.write("\ufeff")  # BOM de Excel doc dung tieng Viet
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(["" if v is None else v for v in row])
    return response


def xlsx_response(filename, headers, rows, sheet="Data"):
    try:
        from openpyxl import Workbook
    except ImportError:
        return HttpResponse("Chua cai openpyxl. Chay: pip install openpyxl", status=501, content_type="text/plain")
    wb = Workbook()
    ws = wb.active
    ws.title = sheet[:31]
    ws.append(list(headers))
    for row in rows:
        ws.append([_cell(v) for v in row])
    response = HttpResponse(content_type=XLSX_MIME)
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    wb.save(response)
    return response


def export_response(request, filename, headers, rows):
    """Chon CSV hoac Excel theo ?format=csv|xlsx (mac dinh csv), them dau thoi gian vao ten file."""
    stamp = timezone.now().strftime("%Y%m%d_%H%M")
    name = f"{filename}_{stamp}"
    if request.GET.get("format", "csv").lower() == "xlsx":
        return xlsx_response(name, headers, rows)
    return csv_response(name, headers, rows)
