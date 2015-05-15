from rest_framework.permissions import BasePermission

from .utils import get_tenant_properties

class TenantConditionalOpenClose(BasePermission):
    """
    Allows access only to authenticated users.
    """

    def has_permission(self, request, view):
        try:
            if get_tenant_properties().CLOSED_SITE:
                return request.user and request.user.is_authenticated()
        except AttributeError:
            pass
        return True
