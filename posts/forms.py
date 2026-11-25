from typing import Any, ClassVar

from django import forms
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from core.forms import MultipleFileField
from core.images import process_image
from posts.models import MAX_IMAGES_PER_POST, Post, PostImage
from universities.models import Course


class PostForm(forms.ModelForm[Post]):
    images = MultipleFileField(
        label=_("Pictures (optional)"),
        required=False,
        help_text=_("Up to 4 JPEG, PNG or WebP images, 5 MB each. Location data is removed."),
    )

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
        self.processed_images: list[Any] = []
        if self.instance.pk is not None:
            del self.fields["images"]  # pictures are added when posting, not on edit
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

    def clean_images(self) -> list[Any]:
        files: list[Any] = self.cleaned_data.get("images") or []
        if len(files) > MAX_IMAGES_PER_POST:
            raise forms.ValidationError(_("You can add at most 4 pictures."))
        self.processed_images = [process_image(f) for f in files]
        return files

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
            for position, content in enumerate(self.processed_images):
                PostImage.objects.create(post=post, image=content, position=position)
        return post
