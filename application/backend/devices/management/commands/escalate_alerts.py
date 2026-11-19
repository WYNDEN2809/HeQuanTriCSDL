from django.core.management.base import BaseCommand
from django.utils import timezone

from devices.alert_services import is_overdue, overdue_q
from devices.models import Alert
from reports.notifications import notify_brand, retry_pending_emails


class Command(BaseCommand):
    help = "Notify brand administrators and operations managers about overdue unresolved alerts."

    def handle(self, *args, **options):
        now = timezone.now()
        emails_attempted = retry_pending_emails()
        # Materialize IDs before creating nested transactions/writes; SQL Server cannot
        # savepoint a connection while an iterator still has an active result set.
        alert_ids = list(Alert.objects.filter(overdue_q(now)).values_list("pk", flat=True))
        notifications = 0
        for alert_id in alert_ids:
            alert = Alert.objects.select_related("machine").get(pk=alert_id)
            if not is_overdue(alert, now):
                continue
            created = notify_brand(
                brand_id=alert.machine.brand_id,
                event_key=f"alert:{alert.pk}:sla-escalated",
                title=f"Cảnh báo #{alert.pk} đã quá hạn SLA",
                message=f"{alert.alert_type} tại máy {alert.machine.name} vẫn chưa được xử lý.",
                target_url=f"/portal/alerts/{alert.pk}/",
            )
            notifications += len(created)
        self.stdout.write(self.style.SUCCESS(
            f"Đã tạo {notifications} thông báo leo thang SLA; thử gửi {emails_attempted} email đang chờ."
        ))
