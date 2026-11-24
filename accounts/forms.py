"""allauth forms with our own labels, so they are translated by our catalogue."""

from typing import Any

from allauth.account import forms as allauth_forms
from django import forms
from django.utils.translation import gettext_lazy as _


class SignupForm(allauth_forms.SignupForm):  # type: ignore[misc]
    display_name = forms.CharField(
        label=_("Your name"),
        max_length=60,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
        help_text=_("How other people on CampusQ will see you."),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        email = self.fields["email"]
        email.label = _("University email")
        email.help_text = _("The address your university gave you, ending in .edu.al.")
        email.widget.attrs["placeholder"] = "emer_mbiemer@unitir.edu.al"
        self.fields["password1"].label = _("Password")
        self.fields["password2"].label = _("Password (again)")
        for field in ("password1", "password2"):
            self.fields[field].widget.attrs.pop("placeholder", None)
        self.order_fields(["display_name", "email", "password1", "password2"])

    def clean_display_name(self) -> str:
        name: str = " ".join(self.cleaned_data["display_name"].split())
        if not name:
            raise forms.ValidationError(_("Please enter your name."))
        return name


class LoginForm(allauth_forms.LoginForm):  # type: ignore[misc]
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["login"].label = _("Email")
        self.fields["login"].widget.attrs.pop("placeholder", None)
        self.fields["password"].label = _("Password")
        self.fields["password"].help_text = ""  # the template links to the reset page
        self.fields["password"].widget.attrs.pop("placeholder", None)
        self.fields["remember"].label = _("Keep me signed in")


class ResetPasswordForm(allauth_forms.ResetPasswordForm):  # type: ignore[misc]
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].label = _("Email")
        self.fields["email"].widget.attrs.pop("placeholder", None)


class ResetPasswordKeyForm(allauth_forms.ResetPasswordKeyForm):  # type: ignore[misc]
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = _("New password")
        self.fields["password2"].label = _("New password (again)")
        for field in ("password1", "password2"):
            self.fields[field].widget.attrs.pop("placeholder", None)


class ChangePasswordForm(allauth_forms.ChangePasswordForm):  # type: ignore[misc]
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["oldpassword"].label = _("Current password")
        self.fields["password1"].label = _("New password")
        self.fields["password2"].label = _("New password (again)")
        for field in ("oldpassword", "password1", "password2"):
            self.fields[field].widget.attrs.pop("placeholder", None)
