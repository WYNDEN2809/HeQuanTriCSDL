from catalog.models import Brand

from .models import BrandMember

SESSION_KEY = "active_brand_id"


class ActiveBrandMiddleware:
    """
    Gan vao moi request:
      request.available_brands : danh sach brand user duoc phep thao tac
      request.active_brand     : brand dang chon (None = tat ca, chi danh cho super admin)
      request.active_brand_id
      request.brand_role       : vai tro trong brand dang chon ('PLATFORM_ADMIN' voi super admin)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.available_brands = []
        request.active_brand = None
        request.active_brand_id = None
        request.brand_role = None

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            self._resolve(request, user)
        return self.get_response(request)

    @staticmethod
    def _resolve(request, user):
        selected = request.session.get(SESSION_KEY)

        if user.is_platform_admin:
            brands = list(Brand.objects.filter(is_active=True).order_by("name"))
            request.available_brands = brands
            request.active_brand = next((b for b in brands if b.id == selected), None)
            request.brand_role = "PLATFORM_ADMIN"
        else:
            memberships = list(
                BrandMember.objects.filter(user=user, brand__is_active=True)
                .select_related("brand")
                .order_by("brand__name")
            )
            request.available_brands = [m.brand for m in memberships]
            chosen = next((m for m in memberships if m.brand_id == selected), None)
            if chosen is None and memberships:
                chosen = memberships[0]
            if chosen is not None:
                request.active_brand = chosen.brand
                request.brand_role = chosen.brand_role

        request.active_brand_id = request.active_brand.id if request.active_brand else None
