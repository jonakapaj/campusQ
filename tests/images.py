"""Build test images in memory."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

GPS_IFD = 0x8825


def jpeg_with_gps(
    name: str = "photo.jpg", size: tuple[int, int] = (800, 600)
) -> SimpleUploadedFile:
    img = Image.new("RGB", size, (200, 30, 40))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # Make
    exif.get_ifd(GPS_IFD).update({1: "N", 2: (41.0, 19.0, 44.0), 3: "E", 4: (19.0, 49.0, 5.0)})
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif.tobytes())
    return SimpleUploadedFile(name, out.getvalue(), content_type="image/jpeg")


def png(
    name: str = "pic.png", size: tuple[int, int] = (300, 200), mode: str = "RGBA"
) -> SimpleUploadedFile:
    out = io.BytesIO()
    Image.new(mode, size, (0, 128, 0, 128) if mode == "RGBA" else (0, 128, 0)).save(
        out, format="PNG"
    )
    return SimpleUploadedFile(name, out.getvalue(), content_type="image/png")


def gif(name: str = "anim.gif") -> SimpleUploadedFile:
    out = io.BytesIO()
    Image.new("P", (10, 10)).save(out, format="GIF")
    return SimpleUploadedFile(name, out.getvalue(), content_type="image/gif")
