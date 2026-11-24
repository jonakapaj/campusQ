from typing import Any, ClassVar

from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError
from django.forms import Form
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from universities.domains import is_signup_allowed


class AccountAdapter(DefaultAccountAdapter):  # type: ignore[misc]
    # allauth has no Albanian catalogue, so the messages users can reach are redefined
    # here, where our makemessages picks them up.
    error_messages: ClassVar[dict[str, Any]] = {
        **DefaultAccountAdapter.error_messages,
        "account_inactive": _("This account is currently inactive."),
        "email_password_mismatch": _("The email address and/or password are not correct."),
        "email_taken": _("A user is already registered with this email address."),
        "enter_current_password": _("Please type your current password."),
        "incorrect_code": _("Incorrect code."),
        "incorrect_password": _("Incorrect password."),
        "invalid_or_expired_key": _("Invalid or expired key."),
        "invalid_password_reset": _("The password reset link was invalid."),
        "max_email_addresses": _("You cannot add more than %d email addresses."),
        "rate_limited": _("Too many requests. Please wait a little and try again."),
        "same_as_current": _("The new value must be different from the current one."),
        "too_many_login_attempts": _("Too many failed sign-in attempts. Try again later."),
        "unknown_email": _("The email address is not assigned to any user account."),
        "unverified_primary_email": _("Your email address must be verified."),
    }

    def clean_email(self, email: str) -> str:
        email = super().clean_email(email)
        if not is_signup_allowed(email):
            raise ValidationError(
                _("Use your university email address (ending in .edu.al)."),
                code="email_not_academic",
            )
        return email

    def save_user(self, request: HttpRequest, user: User, form: Form, commit: bool = True) -> User:
        user = super().save_user(request, user, form, commit=False)
        # Only fields we choose are copied from the form: role, staff and professor
        # status always keep their safe model defaults at signup.
        user.display_name = form.cleaned_data.get("display_name", "")
        if commit:
            user.save()
        return user
