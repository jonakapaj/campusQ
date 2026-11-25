from typing import Any, ClassVar

from django import forms
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from posts.models import Post
from universities.models import Course


class PostForm(forms.ModelForm[Post]):
    class Meta:
        model = Post
        fields = ("course", "body")
        labels: ClassVar[dict[str, Promise]] = {
            "course": _("Course (optional)"),
            "body": _("What's on your mind?"),
        }
        help_texts: ClassVar[dict[str, Promise]] = {
            "body": _("Markdown works: **bold**, *italic*, `code`, lists and links."),
        }
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "body": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args: Any, author: User, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.author = author
        course = self.fields["course"]
        if isinstance(course, forms.ModelChoiceField):
            # Only courses of the author's university; anything else is an invalid choice.
            course.queryset = Course.objects.filter(university=author.university).order_by("name")
            course.empty_label = _("No course")

    def clean_body(self) -> str:
        body: str = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError(_("Write something first."))
        return body

    def save(self, commit: bool = True) -> Post:
        post = super().save(commit=False)
        if post.pk is None:
            # Server-side only: the author and university never come from the form.
            post.author = self.author
            if self.author.university is None:
                raise ValueError("Only members of a university can post")
            post.university = self.author.university
        if commit:
            post.save()
            self.save_m2m()
        return post
