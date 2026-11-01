from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


def normalize_email(value):
    return value.strip().lower()


class EmailAuthenticationBackend(ModelBackend):
    """Authenticate only against a normalized email address."""

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        candidate = email if email is not None else username
        if not candidate or password is None:
            return None

        normalized_email = normalize_email(candidate)
        UserModel = get_user_model()
        try:
            user = UserModel._default_manager.get(email__iexact=normalized_email)
        except UserModel.DoesNotExist:
            # Match Django's password-hash timing behavior for unknown users.
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
