"""Custom DRF permissions for the articles app."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsStaffOrReadOnly(BasePermission):
    """Anyone can read; only staff users can create, update or delete."""

    def has_permission(self, request, view):
        # GET, HEAD, and OPTIONS never change data, so allow everyone
        if request.method in SAFE_METHODS:
            return True
        # Writes require a logged-in staff user; anonymous users have is_staff = False
        return bool(request.user and request.user.is_staff)
