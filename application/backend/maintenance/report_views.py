"""Bao cao bao tri (Nguoi 5, Buoc 5): downtime, hong lap lai, tan suat, thoi gian xu ly."""
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.shortcuts import render
from django.utils import timezone

from accounts import roles
from accounts.permissions import brand_role_required, scope_queryset

from . import services as svc
from .models import MaintenanceRecord as Record

REPEAT_THRESHOLD = 3   # tu 3 phieu trong ky tro len = hong lap lai


def _date(value, default):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def build_report(request, d_from, d_to):
    qs = scope_queryset(Record.objects.select_related("machine", "alert"), request, "machine__brand_id").filter(
        created_at__gte=d_from, created_at__lt=d_to + timedelta(days=1))
    per_machine = defaultdict(lambda: {"tickets": 0, "downtime_h": 0.0, "completed": 0, "types": defaultdict(int)})
    by_priority = defaultdict(lambda: {"n": 0, "hours": 0.0, "done": 0})
    by_month = defaultdict(int)
    overdue = 0
    now = timezone.now()
    for t in qs[:50000]:
        m = per_machine[t.machine.name]
        m["tickets"] += 1
        m["types"][t.maintenance_type] += 1
        by_month[t.created_at.strftime("%Y-%m")] += 1
        p = svc.priority_of(t)
        by_priority[p]["n"] += 1
        if t.status == Record.Status.COMPLETED and t.completed_at:
            hours = (t.completed_at - t.created_at).total_seconds() / 3600.0
            m["downtime_h"] += hours
            m["completed"] += 1
            by_priority[p]["hours"] += hours
            by_priority[p]["done"] += 1
        if svc.is_overdue(t, now):
            overdue += 1
    machines = [{"name": k, **v, "downtime_h": round(v["downtime_h"], 1), "repeat": v["tickets"] >= REPEAT_THRESHOLD,
                 "avg_h": round(v["downtime_h"] / v["completed"], 1) if v["completed"] else None}
                for k, v in per_machine.items()]
    machines.sort(key=lambda x: (-x["tickets"], x["name"]))
    priorities = [{"priority": p, "n": by_priority[p]["n"],
                   "avg_h": round(by_priority[p]["hours"] / by_priority[p]["done"], 1) if by_priority[p]["done"] else None}
                  for p in ("CRITICAL", "HIGH", "MEDIUM", "LOW") if by_priority[p]["n"]]
    total_done = sum(v["done"] for v in by_priority.values())
    avg_all = round(sum(v["hours"] for v in by_priority.values()) / total_done, 1) if total_done else None
    return {"machines": machines, "priorities": priorities, "months": sorted(by_month.items()),
            "total": sum(v["n"] for v in by_priority.values()), "overdue": overdue, "avg_hours": avg_all,
            "repeat_machines": [m for m in machines if m["repeat"]]}


@brand_role_required(*roles.MAINT_REPORTS)
def maintenance_report(request):
    today = date.today()
    d_from = _date(request.GET.get("from"), today - timedelta(days=89))
    d_to = _date(request.GET.get("to"), today)
    data = build_report(request, d_from, d_to)
    if request.GET.get("export"):
        from reports.exports import export_response  # Nguoi 3

        rows = ([m["name"], m["tickets"], m["completed"], m["downtime_h"], m["avg_h"] if m["avg_h"] is not None else "",
                 "X" if m["repeat"] else ""] for m in data["machines"])
        return export_response(request, "maintenance_report",
                               ["May", "So phieu", "Da hoan thanh", "Downtime (gio)", "TB xu ly (gio)", "Hong lap lai"], rows)
    data.update({"d_from": d_from.isoformat(), "d_to": d_to.isoformat(), "threshold": REPEAT_THRESHOLD})
    return render(request, "portal/maintenance/report.html", data)
