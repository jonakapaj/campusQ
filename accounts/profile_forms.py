from typing import Any, ClassVar

from django import forms
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from core.images import process_image
from universities.models import Faculty


class ProfileForm(forms.ModelForm[User]):
    """Only these fields are editable: role, email, university and status never are."""

    photo = forms.FileField(
        label=_("Photo"),
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        help_text=_("JPEG, PNG or WebP, up to 5 MB. It is cropped to a square."),
    )
    remove_photo = forms.BooleanField(label=_("Remove my photo"), required=False)

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
        self.processed_photo: Any = None
        if not self.instance.avatar:
            del self.fields["remove_photo"]
        faculty = self.fields["faculty"]
        if isinstance(faculty, forms.ModelChoiceField):
            # Only faculties of the user's own university are offered, and anything else
            # posted is rejected as an invalid choice.
            faculty.queryset = Faculty.objects.filter(university=self.instance.university)
            faculty.empty_label = _("Not set")

    def clean_photo(self) -> Any:
        upload = self.cleaned_data.get("photo")
        self.processed_photo = process_image(upload, square=256) if upload else None
        return upload

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        if self.processed_photo is not None or self.cleaned_data.get("remove_photo"):
            if user.avatar:
                user.avatar.delete(save=False)
            user.avatar = self.processed_photo or ""
        if commit:
            user.save()
        return user

    def clean_display_name(self) -> str:
        name: str = " ".join(self.cleaned_data["display_name"].split())
        if not name:
            raise forms.ValidationError(_("Please enter your name."))
        return name
