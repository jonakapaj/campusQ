import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

ALBANIAN_HEADING = "Mirë se vini në CampusQ"
ENGLISH_HEADING = "Welcome to CampusQ"


def test_albanian_is_the_default(client: Client) -> None:
    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert response["Content-Language"] == "sq"
    assert '<html lang="sq">' in response.content.decode()
    assert ALBANIAN_HEADING in response.content.decode()


def test_browser_language_does_not_override_default(client: Client) -> None:
    # Most students' devices send Accept-Language: en. They should still see Albanian.
    response = client.get(reverse("home"), HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")

    assert response["Content-Language"] == "sq"
    assert ALBANIAN_HEADING in response.content.decode()


def test_explicit_english_choice_is_respected(client: Client) -> None:
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"

    response = client.get(reverse("home"))

    assert response["Content-Language"] == "en"
    assert ENGLISH_HEADING in response.content.decode()


@pytest.mark.parametrize("cookie", ["de", "fr", "<script>", ""])
def test_unsupported_cookie_falls_back_to_albanian(client: Client, cookie: str) -> None:
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = cookie

    response = client.get(reverse("home"))

    assert response["Content-Language"] == "sq"


def test_response_varies_on_cookie(client: Client) -> None:
    # Otherwise a shared cache could serve one user's language to another.
    response = client.get(reverse("home"))

    assert "Cookie" in response["Vary"]


def test_set_language_view_switches_language(client: Client) -> None:
    response = client.post(reverse("set_language"), {"language": "en", "next": "/"}, follow=True)

    assert client.cookies[settings.LANGUAGE_COOKIE_NAME].value == "en"
    assert ENGLISH_HEADING in response.content.decode()


def test_language_switcher_lists_languages_in_their_own_name(client: Client) -> None:
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"

    html = client.get(reverse("home")).content.decode()

    assert ">Shqip</option>" in html
    assert ">English</option>" in html


def test_pages_are_not_indexable(client: Client) -> None:
    html = client.get(reverse("home")).content.decode()

    assert '<meta name="robots" content="noindex, nofollow">' in html


def test_albanian_characters_render_correctly(client: Client) -> None:
    response = client.get(reverse("home"))

    assert response["Content-Type"] == "text/html; charset=utf-8"
    assert "ë" in response.content.decode("utf-8")
