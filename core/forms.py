from typing import Any

from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """A file input that accepts several files; cleans to a list."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault(
            "widget", MultipleFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"})
        )
        super().__init__(*args, **kwargs)

    def clean(self, data: Any, initial: Any = None) -> list[Any]:
        if not data:
            if self.required:
                raise forms.ValidationError(self.error_messages["required"], code="required")
            return []
        files = data if isinstance(data, list | tuple) else [data]
        return [super(MultipleFileField, self).clean(f, initial) for f in files]
