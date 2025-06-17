"""
Разрешения для API
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение только для владельца объекта для записи.
    Чтение разрешено всем аутентифицированным пользователям.
    """
    
    def has_object_permission(self, request, view, obj):
        # Разрешения на чтение для всех аутентифицированных пользователей
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Разрешения на запись только для владельца объекта
        return hasattr(obj, 'user') and obj.user == request.user


class IsOwner(permissions.BasePermission):
    """
    Разрешение только для владельца объекта
    """
    
    def has_object_permission(self, request, view, obj):
        return hasattr(obj, 'user') and obj.user == request.user


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Разрешение для владельца объекта или администратора
    """
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return hasattr(obj, 'user') and obj.user == request.user 