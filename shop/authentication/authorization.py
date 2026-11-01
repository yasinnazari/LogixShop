from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404


def require_permission(user, permission):
    """Use Django permissions rather than role-name checks for protected actions."""
    if not user.is_authenticated or not user.has_perm(permission):
        raise PermissionDenied


def get_owned_object_or_404(model, *, user, **lookup):
    """Ownership-scoped lookup for future address/order detail views to prevent IDOR."""
    return get_object_or_404(model, user=user, **lookup)
