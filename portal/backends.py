from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsernameOrEmailBackend(ModelBackend):
    """Autentica por nome de usuário ou por um e-mail não ambíguo."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (username or kwargs.get("email") or "").strip()
        if not identifier or password is None:
            return None

        user_model = get_user_model()
        candidates = user_model._default_manager.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).distinct()
        if candidates.count() != 1:
            return None

        user = candidates.first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
