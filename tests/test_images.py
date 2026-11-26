import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from PIL import Image

from accounts.models import User
from core import images
from core.images import process_image
from posts.models import Post, PostImage
from tests.factories import PostFactory, UniversityFactory, UserFactory
from tests.images import GPS_IFD, gif, jpeg_with_gps, png
from universities.models import University


def _open(content: bytes) -> Image.Image:
    return Image.open(io.BytesIO(content))


def test_reencoding_strips_exif_and_gps() -> None:
    upload = jpeg_with_gps()
    assert _open(upload.read()).getexif().get_ifd(GPS_IFD)  # the input really has GPS
    upload.seek(0)

    out = process_image(upload)

    img = _open(out.read())
    assert img.format == "WEBP"
    assert not img.getexif()
    assert not img.getexif().get_ifd(GPS_IFD)
    name = str(out.name)
    assert name.endswith(".webp")
    assert "photo" not in name  # random name, not the user's file name


def test_large_images_are_resized() -> None:
    out = process_image(jpeg_with_gps(size=(4000, 3000)))

    assert max(_open(out.read()).size) == 1600


def test_square_crop_for_avatars() -> None:
    out = process_image(jpeg_with_gps(size=(800, 600)), square=256)

    assert _open(out.read()).size == (256, 256)


def test_transparent_png_is_flattened() -> None:
    out = process_image(png())

    assert _open(out.read()).mode == "RGB"


@pytest.mark.parametrize(
    "upload",
    [
        SimpleUploadedFile("x.jpg", b"<?php echo 'hi'; ?>", content_type="image/jpeg"),
        SimpleUploadedFile("x.png", b"\x89PNG\r\n\x1a\n" + b"garbage" * 10),
        SimpleUploadedFile("x.svg", b"<svg onload=alert(1)></svg>", content_type="image/svg+xml"),
    ],
)
def test_non_images_are_rejected(upload: SimpleUploadedFile) -> None:
    with pytest.raises(ValidationError):
        process_image(upload)


def test_gif_is_rejected() -> None:
    with pytest.raises(ValidationError, match="JPEG, PNG"):
        process_image(gif())


def test_too_large_file_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(images, "MAX_UPLOAD_BYTES", 100)

    with pytest.raises(ValidationError, match="5 MB"):
        process_image(jpeg_with_gps())


def test_decompression_bomb_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(images, "MAX_PIXELS", 1000)

    with pytest.raises(ValidationError):
        process_image(jpeg_with_gps(size=(100, 100)))


@pytest.fixture
def uni() -> University:
    return UniversityFactory.create()


@pytest.fixture
def ana(uni: University) -> User:
    return UserFactory.create(university=uni)


@pytest.mark.django_db
def test_post_with_pictures(client: Client, ana: User) -> None:
    client.force_login(ana)

    client.post(reverse("post_create"), {"body": "Foto", "images": [jpeg_with_gps(), png()]})

    post = Post.objects.get()
    assert [i.position for i in post.images.all()] == [0, 1]
    assert all(i.image.name.endswith(".webp") for i in post.images.all())
    assert post.images.first().width > 0  # type: ignore[union-attr]


@pytest.mark.django_db
def test_at_most_four_pictures(client: Client, ana: User) -> None:
    client.force_login(ana)

    client.post(reverse("post_create"), {"body": "x", "images": [png() for _ in range(5)]})

    assert not Post.objects.exists()


@pytest.mark.django_db
def test_invalid_picture_rejects_the_post(client: Client, ana: User) -> None:
    client.force_login(ana)
    bad = SimpleUploadedFile("x.jpg", b"nope", content_type="image/jpeg")

    response = client.post(reverse("post_create"), {"body": "x", "images": [bad]})

    assert response.status_code == 200
    assert not Post.objects.exists()


@pytest.fixture
def post_image(ana: User) -> PostImage:
    post = PostFactory.create(author=ana)
    return PostImage.objects.create(post=post, image=process_image(png()))


@pytest.mark.django_db
def test_classmates_can_load_post_pictures(
    client: Client, post_image: PostImage, uni: University
) -> None:
    client.force_login(UserFactory.create(university=uni))

    response = client.get(post_image.image.url)

    assert response.status_code == 200
    assert response["Content-Type"] == "image/webp"
    assert "private" in response["Cache-Control"]


@pytest.mark.django_db
def test_other_universities_cannot_load_post_pictures(
    client: Client, post_image: PostImage
) -> None:
    client.force_login(UserFactory.create(university=UniversityFactory.create()))

    assert client.get(post_image.image.url).status_code == 404


@pytest.mark.django_db
def test_logged_out_visitors_cannot_load_media(client: Client, post_image: PostImage) -> None:
    response = client.get(post_image.image.url)

    assert response.status_code == 302


@pytest.mark.django_db
def test_hidden_post_pictures_are_not_served(
    client: Client, post_image: PostImage, uni: University
) -> None:
    Post.objects.filter(pk=post_image.post_id).update(is_hidden=True)
    client.force_login(UserFactory.create(university=uni))

    assert client.get(post_image.image.url).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path", ["../../config/settings.py", "posts/../../.env", "posts/nope.webp", "other/x.webp"]
)
def test_unknown_or_traversal_paths_are_404(client: Client, ana: User, path: str) -> None:
    client.force_login(ana)

    assert client.get(f"/media/{path}").status_code == 404


@pytest.mark.django_db
def test_deleting_a_post_deletes_its_files(post_image: PostImage) -> None:
    name = post_image.image.name
    assert default_storage.exists(name)

    post_image.post.delete()

    assert not default_storage.exists(name)


@pytest.mark.django_db
def test_upload_avatar_replace_and_remove(client: Client, ana: User) -> None:
    client.force_login(ana)
    url = reverse("profile_edit")

    client.post(url, {"display_name": "Ana", "photo": jpeg_with_gps()})
    ana.refresh_from_db()
    first = ana.avatar.name
    assert first.startswith("avatars/")
    assert default_storage.exists(first)
    assert client.get(ana.avatar.url).status_code == 200

    client.post(url, {"display_name": "Ana", "photo": png()})
    ana.refresh_from_db()
    assert ana.avatar.name != first
    assert not default_storage.exists(first)  # old file removed

    second = ana.avatar.name
    client.post(url, {"display_name": "Ana", "remove_photo": "on"})
    ana.refresh_from_db()
    assert not ana.avatar
    assert not default_storage.exists(second)


@pytest.mark.django_db
def test_avatars_are_visible_across_universities(client: Client, ana: User) -> None:
    ana.avatar = process_image(png(), square=256)
    ana.save()
    client.force_login(UserFactory.create(university=UniversityFactory.create()))

    assert client.get(ana.avatar.url).status_code == 200


@pytest.mark.django_db
def test_suspended_users_avatar_is_not_served(client: Client, ana: User) -> None:
    ana.avatar = process_image(png(), square=256)
    ana.is_active = False
    ana.save()
    client.force_login(UserFactory.create())

    assert client.get(ana.avatar.url).status_code == 404


@pytest.mark.django_db
def test_deleting_a_user_deletes_their_avatar(ana: User) -> None:
    ana.avatar = process_image(png(), square=256)
    ana.save()
    name = ana.avatar.name

    ana.delete()

    assert not default_storage.exists(name)
