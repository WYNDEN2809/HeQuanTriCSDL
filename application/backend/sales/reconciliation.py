"""Doi chieu giao dich noi bo voi file bao cao cua nha cung cap thanh toan (Nguoi 4)."""
import csv
import io
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from accounts.permissions import scope_queryset
from accounts.portal_utils import PortalError

from .models import Payment

REQUIRED = ("provider_transaction_id", "amount", "status")
MAX_ROWS = 50000


def parse_provider_csv(uploaded):
    """Doc CSV cua nha cung cap. Cot bat buoc: provider_transaction_id, amount, status. Tuy chon: payment_reference."""
    try:
        text = uploaded.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise PortalError("File phải được lưu ở dạng UTF-8.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise PortalError("File rỗng.")
    fields = {(f or "").strip().lower(): f for f in reader.fieldnames}
    missing = [c for c in REQUIRED if c not in fields]
    if missing:
        raise PortalError("Thiếu cột bắt buộc: " + ", ".join(missing))
    rows = []
    for i, raw in enumerate(reader, start=2):
        if i > MAX_ROWS:
            raise PortalError(f"File quá lớn (tối đa {MAX_ROWS} dòng).")
        try:
            rows.append({
                "txn": (raw[fields["provider_transaction_id"]] or "").strip(),
                "amount": Decimal((raw[fields["amount"]] or "0").strip()),
                "status": (raw[fields["status"]] or "").strip().upper(),
                "reference": (raw[fields["payment_reference"]] or "").strip() if "payment_reference" in fields else "",
            })
        except InvalidOperation:
            raise PortalError(f"Dòng {i}: số tiền không hợp lệ.")
    return rows


def reconcile(request, provider_rows, d_from, d_to):
    """
    So khop theo provider_transaction_id. Tra ve dict cac nhom:
      matched, amount_mismatch, status_mismatch, reference_mismatch, missing_internal, missing_provider.
    """
    internal = (
        scope_queryset(Payment.objects.select_related("order"), request, "order__machine_slot__machine__brand_id")
        .filter(created_at__gte=d_from, created_at__lt=d_to + timedelta(days=1))
    )
    by_txn = {p.provider_transaction_id: p for p in internal}
    seen = set()
    out = {k: [] for k in ("matched", "amount_mismatch", "status_mismatch", "reference_mismatch",
                           "missing_internal", "missing_provider")}
    for r in provider_rows:
        p = by_txn.get(r["txn"])
        seen.add(r["txn"])
        if p is None:
            out["missing_internal"].append({"txn": r["txn"], "reference": r["reference"], "p_amount": r["amount"],
                                            "p_status": r["status"], "i_amount": None, "i_status": None})
            continue
        row = {"txn": r["txn"], "reference": p.order.payment_reference, "p_amount": r["amount"],
               "p_status": r["status"], "i_amount": p.amount, "i_status": p.status}
        if r["amount"] != p.amount:
            out["amount_mismatch"].append(row)
        elif r["status"] != p.status:
            out["status_mismatch"].append(row)
        elif r["reference"] and r["reference"] != p.order.payment_reference:
            out["reference_mismatch"].append(row)
        else:
            out["matched"].append(row)
    for txn, p in by_txn.items():
        if txn not in seen and p.method != "FREE_TRIAL" and p.status in (Payment.Status.SUCCESS, Payment.Status.REFUNDED):
            out["missing_provider"].append({"txn": txn, "reference": p.order.payment_reference, "p_amount": None,
                                            "p_status": None, "i_amount": p.amount, "i_status": p.status})
    return out


LABELS = {
    "matched": "Khớp", "amount_mismatch": "Lệch số tiền", "status_mismatch": "Lệch trạng thái",
    "reference_mismatch": "Lệch mã đơn", "missing_internal": "Có ở nhà cung cấp, thiếu ở hệ thống",
    "missing_provider": "Có ở hệ thống, thiếu ở nhà cung cấp",
}


def flatten_mismatches(result):
    """Danh sach dong (chuoi) cho xuat file: chi gom cac nhom bi lech."""
    rows = []
    for key in ("amount_mismatch", "status_mismatch", "reference_mismatch", "missing_internal", "missing_provider"):
        for r in result[key]:
            rows.append([key, r["txn"], r["reference"],
                         "" if r["i_amount"] is None else str(r["i_amount"]), r["i_status"] or "",
                         "" if r["p_amount"] is None else str(r["p_amount"]), r["p_status"] or ""])
    return rows
