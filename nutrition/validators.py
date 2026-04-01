from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class NoWhitespacePasswordValidator:
    def validate(self, password, user=None):
        if len(password) > 128:
            raise ValidationError(
                _("Password must not be longer than 128 characters."),
                code="password_too_long",
            )

        if password != password.strip():
            raise ValidationError(
                _("Password must not start or end with spaces."),
                code="password_has_outer_spaces",
            )

        if any(char.isspace() for char in password):
            raise ValidationError(
                _("Password must not contain spaces."),
                code="password_has_spaces",
            )

        if not any(char.isdigit() for char in password):
            raise ValidationError(
                _("Password must contain at least one digit."),
                code="password_missing_digit",
            )

        if not any(char.islower() for char in password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code="password_missing_lowercase",
            )

        if not any(char.isupper() for char in password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code="password_missing_uppercase",
            )

    def get_help_text(self):
        return _("Your password must meet complexity requirements.")