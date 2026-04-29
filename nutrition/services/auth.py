import secrets

from django.contrib.auth import get_user_model
from django.utils import timezone

from nutrition.models import UserProfile
from nutrition.services.email_service import (
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)


def prepare_email_verification(user) -> UserProfile:
    profile = user.profile
    profile.is_verified = False
    profile.verified_at = None
    profile.verification_token = secrets.token_urlsafe(32)
    profile.save()

    return profile


def send_registration_verification(user) -> None:
    profile = prepare_email_verification(user)
    send_verification_email(user, profile.verification_token)


def verify_email_token(token: str | None) -> tuple[bool, str]:
    if not token:
        return False, "Verification token is required."

    try:
        profile = UserProfile.objects.select_related("user").get(
            verification_token=token,
        )
    except UserProfile.DoesNotExist:
        return False, "Invalid verification token."

    profile.is_verified = True
    profile.verified_at = timezone.now()
    profile.verification_token = None
    profile.save()

    send_welcome_email(profile.user)

    return True, "Email verified successfully."


def request_password_reset(email: str) -> None:
    user_model = get_user_model()
    user = user_model.objects.filter(email=email).first()

    if not user or not hasattr(user, "profile"):
        return

    token = secrets.token_urlsafe(32)
    profile = user.profile
    profile.password_reset_token = token
    profile.password_reset_requested_at = timezone.now()
    profile.save()

    send_password_reset_email(user, token)


def reset_password_by_token(*, token: str, new_password: str) -> bool:
    profile = (
        UserProfile.objects
        .filter(password_reset_token=token)
        .select_related("user")
        .first()
    )

    if not profile:
        return False

    user = profile.user
    user.set_password(new_password)
    user.save()

    profile.password_reset_token = None
    profile.password_reset_requested_at = None
    profile.save(update_fields=["password_reset_token", "password_reset_requested_at"])

    return True
