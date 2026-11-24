"""Pick the UI language from an explicit choice only, never from the browser.

Django's LocaleMiddleware falls back to the Accept-Language header. Most students'
browsers and phones are set to English, so that would make English the de facto
default. Here the language is the one the user picked (the `django_language`
cookie set by Django's `set_language` view), otherwise Albanian.
"""

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import translation
from django.utils.cache import patch_vary_headers


class LanguageCookieMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.supported = {code for code, _name in settings.LANGUAGES}

    def __call__(self, request: HttpRequest) -> HttpResponse:
        language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, "")
        if language not in self.supported:
            language = settings.LANGUAGE_CODE

        translation.activate(language)
        request.LANGUAGE_CODE = language
        response = self.get_response(request)

        patch_vary_headers(response, ("Cookie",))
        response.headers.setdefault("Content-Language", language)
        return response
