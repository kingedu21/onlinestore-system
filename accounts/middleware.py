from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and getattr(user, 'must_change_password', False):
            path = request.path
            if self._is_allowed_path(path):
                return self.get_response(request)
            return redirect('password_change')
        return self.get_response(request)

    def _is_allowed_path(self, path: str) -> bool:
        if settings.STATIC_URL and path.startswith(settings.STATIC_URL):
            return True
        if settings.MEDIA_URL and path.startswith(settings.MEDIA_URL):
            return True
        allowed = {
            reverse('password_change'),
            reverse('password_change_done'),
            reverse('logout'),
        }
        if path in allowed:
            return True
        if path.startswith('/admin/logout/'):
            return True
        return False
