from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class NoWhitespacePasswordValidator:
    def validate(self, password, user=None):
        if password != password.strip():
            raise ValidationError(
                _("Password must not start or end with spaces."),
            )

        if any(char.isspace() for char in password):
            raise ValidationError(
                _("Password must not contain spaces."),
            )

    def get_help_text(self):
        return _("Your password must not contain spaces.")