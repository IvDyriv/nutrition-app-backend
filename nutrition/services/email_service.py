from django.conf import settings
from django.core.mail import send_mail


def send_welcome_email(user) -> None:
    subject = "Welcome to Nutrition App"
    message = (
        f"Hello, {user.username}!\n\n"
        "Welcome to Nutrition App.\n"
        "Your account has been created successfully."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_verification_email(user, token: str) -> None:
    verify_url = f"{settings.BACKEND_URL}/api/v1/auth/verify/email/?token={token}"

    subject = "Verify your email"
    message = (
        f"Hello, {user.username}!\n\n"
        "Please verify your email by opening this link:\n"
        f"{verify_url}\n\n"
        "If you did not create this account, ignore this email."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, token: str) -> None:
    reset_url = f"{settings.BACKEND_URL}/api/v1/auth/password-reset/confirm/?token={token}"

    subject = "Reset your password"
    message = (
        f"Hello, {user.username}!\n\n"
        f"To reset your password, open this link:\n"
        f"{reset_url}\n\n"
        f"If you did not request a password reset, ignore this email."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )