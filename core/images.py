"""Validate and re-encode uploaded images.

Every upload is decoded and re-encoded as WebP. That strips EXIF metadata (phones
put the GPS location of a photo there), normalises orientation, and means we never
serve a file in the exact bytes a user sent (no polyglot or disguised files).
"""

import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 40_000_000  # a 40 MP photo is fine; a decompression bomb is not
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def process_image(
    upload: UploadedFile, *, max_side: int = 1600, square: int | None = None
) -> ContentFile[bytes]:
    if upload.size is None or upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError(_("Images can be at most 5 MB."), code="too_large")
    try:
        with Image.open(upload) as probe:
            fmt = probe.format
            width, height = probe.size
            probe.verify()
        if fmt not in ALLOWED_FORMATS:
            raise ValidationError(_("Use a JPEG, PNG or WebP image."), code="format")
        if width * height > MAX_PIXELS:
            raise ValidationError(_("This image is too large."), code="too_many_pixels")
        upload.seek(0)
        with Image.open(upload) as img:
            img.load()
            image = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError) as exc:
        raise ValidationError(_("This file is not a valid image."), code="invalid") from exc

    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")

    if square is not None:
        image = ImageOps.fit(image, (square, square), Image.Resampling.LANCZOS)
    else:
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    image.save(out, format="WEBP", quality=82, method=4)  # no exif= argument: metadata dropped
    return ContentFile(out.getvalue(), name=f"{uuid.uuid4().hex}.webp")
