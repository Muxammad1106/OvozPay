from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework import permissions

from core.utils.auth import authenticate_credentials


def permission(permission):
    def wrapper(func):
        def check(view, request, *args, **kwargs):
            if not request.user.has_perm(permission):
                raise PermissionDenied()

            return func(view, request, *args, **kwargs)

        return check

    return wrapper


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class AuthReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            token = request.headers['Authorization'][6:] if request.headers.get('Authorization') else False
            return authenticate_credentials(token)
        return True
