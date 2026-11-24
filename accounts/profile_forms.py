from typing import Any, ClassVar

from django import forms
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from universities.models import Faculty


class ProfileForm(forms.ModelForm[User]):
    """Only these fields are editable: role, email, university and status never are."""

    class Meta:
        model = User
        fields = ("display_name", "faculty", "field_of_study", "year", "bio")
        labels: ClassVar[dict[str, Promise]] = {
            "display_name": _("Your name"),
            "faculty": _("Faculty"),
            "field_of_study": _("Field of study"),
            "year": _("Year of study"),
            "bio": _("About you"),
        }
        help_texts: ClassVar[dict[str, Promise]] = {
            "field_of_study": _("For example: Computer Science, Law, Medicine."),
            "bio": _("Up to 500 characters. Everyone signed in to CampusQ can see it."),
        }
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "bio": forms.Textarea(attrs={"rows": 4, "maxlength": 500})
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        faculty = self.fields["faculty"]
        if isinstance(faculty, forms.ModelChoiceField):
            # Only faculties of the user's own university are offered, and anything else
            # posted is rejected as an invalid choice.
            faculty.queryset = Faculty.objects.filter(university=self.instance.university)
            faculty.empty_label = _("Not set")

    def clean_display_name(self) -> str:
        name: str = " ".join(self.cleaned_data["display_name"].split())
        if not name:
            raise forms.ValidationError(_("Please enter your name."))
        return name
