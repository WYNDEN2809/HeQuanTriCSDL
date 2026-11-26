from django.urls import path

from .audit_views import audit_list

urlpatterns = [path("", audit_list, name="audit_list")]
