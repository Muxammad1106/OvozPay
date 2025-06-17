from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext as _

from users.models import Token


def authenticate_credentials(key):
    token = Token.objects.select_related('user').filter(key=key, expires_at__gte=timezone.now()).first()

    if token is None:
        raise AuthenticationFailed(_('Invalid or expired token.'))

    if not token.user.is_active:
        raise AuthenticationFailed(_('User inactive or deleted.'))

    if not token.is_active:
        raise AuthenticationFailed(_('Your token is not active.'))

    return True


def check_token_and_create(user, user_agent: str = None):
    tokens = Token.objects.select_related('user').filter(
        user=user,
        expires_at__gte=timezone.now(),
        is_active=True,
    ).count()

    if tokens >= 80:
        raise AuthenticationFailed({"error": "The number of users has been reached."})

    tt = Token.objects.filter(
        user=user,
        user_agent=user_agent,
        expires_at__gte=timezone.now(),
        is_active=True
    )

    if len(tt) > 1:
        tt.update(is_active=False)

    token, _ = Token.objects.get_or_create(
        user=user,
        user_agent=user_agent,
        expires_at__gte=timezone.now(),
        is_active=True
    )

    return token.key
