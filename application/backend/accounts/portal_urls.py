from django.urls import path

from . import portal_views as v

urlpatterns = [
    path("", v.people_list, name="people_list"),
    path("new/", v.people_create, name="people_create"),
    path("<int:pk>/action/", v.people_action, name="people_action"),
]
