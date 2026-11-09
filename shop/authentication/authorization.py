from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404


def require_permission(user, permission):
    if not user.is_authenticated or not user.has_perm(permission):
        raise PermissionDenied


def get_owned_object_or_404(model, *, user, **lookup):
    return get_object_or_404(model, user=user, **lookup)
