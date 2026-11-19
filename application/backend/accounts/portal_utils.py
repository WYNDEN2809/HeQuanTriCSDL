"""Shared helpers for brand-scoped portal pages."""

from django.core.paginator import Paginator

from .permissions import scope_queryset


class PortalError(Exception):
    """An expected validation or workflow error safe to show to portal users."""


def scoped_for_role(request, queryset, brand_field, platform_scope_field=None):
    """Scope rows to the active brand (the view decorator enforces role access)."""
    return scope_queryset(queryset, request, brand_field)


def paginate(request, queryset, per_page=25):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))
